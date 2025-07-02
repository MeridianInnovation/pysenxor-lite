import queue
import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from senxor.thread import CVCamThread, SenxorThread, _BackgroundReader


class TestBackgroundReader:
    @pytest.fixture
    def mock_reader_func(self):
        """Create a mock reader function that returns incremental data."""
        counter = [0]

        def reader():
            counter[0] += 1
            return counter[0]

        return reader

    @pytest.fixture
    def reader(self, mock_reader_func):
        """Create a BackgroundReader instance with the mock reader function."""
        reader = _BackgroundReader(mock_reader_func, "TestReader")
        yield reader
        # Ensure cleanup after each test
        if reader._is_running:
            reader.stop()

    def test_init(self, mock_reader_func):
        """Test that the reader initializes correctly."""
        reader = _BackgroundReader(mock_reader_func, "TestReader")
        assert reader._name == "TestReader"
        assert reader._allow_listener is True
        assert reader._is_running is False
        assert reader._reader_thread is None
        assert reader._latest_data is None
        assert reader._backlog_threshold == 5

        # Test with listener pattern disabled
        reader_no_listener = _BackgroundReader(mock_reader_func, "NoListener", allow_listener=False)
        assert reader_no_listener._allow_listener is False
        assert not hasattr(reader_no_listener, "_listeners")
        assert not hasattr(reader_no_listener, "_backlog_threshold")

    def test_start_stop(self, reader):
        """Test that the reader starts and stops correctly."""
        reader.start()
        assert reader._is_running is True
        assert reader._reader_thread is not None
        assert reader._reader_thread.is_alive()
        assert reader._notifier_thread is not None
        assert reader._is_running is True

        # Test idempotent start
        reader.start()  # Should not create new threads
        assert reader._is_running is True

        reader.stop()
        assert reader._is_running is False
        assert not reader._reader_thread.is_alive()
        assert not reader._notifier_thread.is_alive()

        # Test idempotent stop
        reader.stop()  # Should not raise errors
        assert reader._is_running is False

    def test_read(self, reader):
        """Test that read returns the latest data and consumes it."""
        reader.start()
        # Allow time for the reader to get data
        time.sleep(0.1)

        # First read should return data
        data1 = reader.read()
        assert data1 is not None

        # Second read without new data should return None
        data2 = reader.read()
        assert data2 is None

        # Wait for new data
        time.sleep(0.1)

        # Third read should return new data
        data3 = reader.read()
        assert data3 is not None
        assert data3 > data1  # Counter should have incremented

    def test_listener_pattern(self, reader, mock_reader_func):
        """Test that listeners receive notifications."""
        listener1 = MagicMock()
        listener2 = MagicMock()

        reader = _BackgroundReader(mock_reader_func, "TestReader")
        name1 = reader.add_listener(listener1, "test_listener1")
        name2 = reader.add_listener(listener2)

        assert name1 == "test_listener1"
        assert name2.startswith("listener_")

        data_to_produce = [1, 2, 3]
        reader_func_calls = iter(data_to_produce)
        with patch.object(reader, "_reader_func", side_effect=lambda: next(reader_func_calls, None)):
            reader.start()

            total_expected_listener_calls = len(data_to_produce)
            start_time = time.time()
            while (
                listener1.call_count < total_expected_listener_calls
                or listener2.call_count < total_expected_listener_calls
            ) and (time.time() - start_time < 2):
                time.sleep(0.01)

            assert listener1.call_count == total_expected_listener_calls
            assert listener2.call_count == total_expected_listener_calls

            for i in range(total_expected_listener_calls):
                assert listener1.call_args_list[i].args[0] == data_to_produce[i]
                assert listener2.call_args_list[i].args[0] == data_to_produce[i]

        reader.remove_listener(name1)
        listener1.reset_mock()
        listener2.reset_mock()

        data_to_produce_after_remove = [4, 5]
        reader_func_calls_after_remove = iter(data_to_produce_after_remove)
        with patch.object(reader, "_reader_func", side_effect=lambda: next(reader_func_calls_after_remove, None)):
            start_time = time.time()
            total_expected_listener_calls_after_remove = len(data_to_produce_after_remove)
            while listener2.call_count < total_expected_listener_calls_after_remove and (time.time() - start_time < 2):
                time.sleep(0.01)

        assert listener1.call_count == 0
        assert listener2.call_count == total_expected_listener_calls_after_remove

        for i in range(total_expected_listener_calls_after_remove):
            assert listener2.call_args_list[i].args[0] == data_to_produce_after_remove[i]

        reader.stop()

    def test_listener_errors(self, reader):
        """Test error handling for listener operations."""
        # Test adding a listener with an existing name
        listener = MagicMock()
        name = reader.add_listener(listener, "unique_name")

        with pytest.raises(ValueError, match="A listener with name 'unique_name' already exists"):
            reader.add_listener(listener, "unique_name")

        # Test removing a non-existent listener
        with pytest.raises(KeyError, match="No listener found with name 'nonexistent'"):
            reader.remove_listener("nonexistent")

    def test_disabled_listener_pattern(self, mock_reader_func):
        """Test that operations fail correctly when listener pattern is disabled."""
        reader = _BackgroundReader(mock_reader_func, "NoListener", allow_listener=False)

        with pytest.raises(RuntimeError, match="Listener pattern is disabled for this reader instance"):
            reader.add_listener(MagicMock())

        with pytest.raises(RuntimeError, match="Listener pattern is disabled for this reader instance"):
            reader.remove_listener("any_name")

    def test_slow_listener(self, mock_reader_func):
        """Test that slow listeners cause TimeoutError."""
        reader = _BackgroundReader(mock_reader_func, "SlowListener")
        exception_queue = queue.Queue()

        # Create a slow listener that blocks
        def slow_listener(data):
            time.sleep(0.1)

        reader.add_listener(slow_listener)

        original_notify_loop = reader._notify_loop

        def wrapped_notify_loop():
            try:
                original_notify_loop()
            except Exception as e:
                exception_queue.put(e)
                raise

        # Patch _notify_loop to use our wrapped version
        # Need to re-create the thread so it uses the patched target
        reader._notifying = True
        reader._notifier_thread = threading.Thread(
            target=wrapped_notify_loop,
            name=f"{reader._name}Notify",
            daemon=True,
        )
        reader._notifier_thread.start()

        # Manually start the reader thread to control its lifecycle
        reader._is_running = True
        reader._reader_thread = threading.Thread(
            target=reader._run,
            name=f"{reader._name}Read",
            daemon=True,
        )
        reader._reader_thread.start()

        try:
            caught_exception = exception_queue.get(timeout=5.0)
            assert isinstance(caught_exception, TimeoutError)
            assert "Listener processing backlog exceeded threshold (5 frames)." in str(caught_exception)
        except queue.Empty:
            pytest.fail("TimeoutError was not raised by the notifier thread within the expected time.")
        finally:
            reader.stop()
            if reader._notifier_thread:
                assert not reader._notifier_thread.is_alive()
            if reader._reader_thread:
                assert not reader._reader_thread.is_alive()


class TestSenxorThread:
    @pytest.fixture
    def mock_senxor(self):
        """Create a mock Senxor instance."""
        mock_instance = MagicMock()

        # Configure the mock to return test data
        header = np.zeros(10, dtype=np.float32)
        frame = np.ones((32, 32), dtype=np.float32)
        mock_instance.read.return_value = (header, frame)
        mock_instance.address = "mock_address"

        return mock_instance

    @pytest.fixture
    def senxor_thread(self, mock_senxor):
        """Create a SenxorThread instance with a mock Senxor."""
        thread = SenxorThread(mock_senxor, frame_unit="C")
        yield thread
        # Ensure cleanup
        if thread._started:
            thread.stop()

    def test_init(self):
        """Test that SenxorThread initializes correctly."""
        # Create a mock Senxor instance
        mock_senxor = MagicMock()
        mock_senxor.address = "test_address"

        # Test with default parameters
        thread = SenxorThread(mock_senxor)
        assert thread._celsius is True
        assert thread._started is False
        assert thread._senxor is mock_senxor

        # Test with custom parameters
        thread = SenxorThread(mock_senxor, frame_unit="dK", allow_listener=False)
        assert thread._celsius is False
        assert thread._reader._allow_listener is False
        assert thread._senxor is mock_senxor

    def test_read(self, senxor_thread, mock_senxor):
        """Test that read returns the correct data."""
        # Start the thread first to avoid RuntimeError
        senxor_thread.start()

        # Test when no data is available
        with patch.object(senxor_thread._reader, "read", return_value=None):
            header, frame = senxor_thread.read()
            assert header is None
            assert frame is None

        # Test when data is available
        test_header = np.zeros(10)
        test_frame = np.ones((32, 32))
        with patch.object(senxor_thread._reader, "read", return_value=(test_header, test_frame)):
            header, frame = senxor_thread.read()
            assert header is test_header
            assert frame is test_frame

    def test_start_stop(self, senxor_thread, mock_senxor):
        """Test that start and stop methods work correctly."""
        # Test start
        senxor_thread.start()
        assert senxor_thread._started is True
        mock_senxor.open.assert_called_once()
        mock_senxor.start_stream.assert_called_once()

        # Test idempotent start
        mock_senxor.reset_mock()
        senxor_thread.start()
        mock_senxor.open.assert_not_called()

        # Test stop
        senxor_thread.stop()
        assert senxor_thread._started is False
        mock_senxor.close.assert_called_once()

        # Test idempotent stop
        mock_senxor.reset_mock()
        senxor_thread.stop()
        mock_senxor.close.assert_not_called()

    def test_start_error_handling(self, senxor_thread, mock_senxor):
        """Test error handling during start."""
        mock_senxor.open.side_effect = Exception("Failed to open")

        with pytest.raises(Exception, match="Failed to open"):
            senxor_thread.start()

        assert senxor_thread._started is False
        mock_senxor.close.assert_called_once()

    def test_stop_error_suppression(self, senxor_thread, mock_senxor):
        """Test that errors during stop are suppressed."""
        senxor_thread.start()

        # Setup errors
        mock_senxor.stop_stream.side_effect = Exception("Stop stream error")
        mock_senxor.close.side_effect = Exception("Close error")

        # Should not raise exceptions
        senxor_thread.stop()
        assert senxor_thread._started is False

    def test_read_senxor(self, senxor_thread, mock_senxor):
        """Test the _read_senxor method."""
        # Test successful read
        header = np.zeros(10)
        frame = np.ones((32, 32))
        mock_senxor.read.return_value = (header, frame)

        result = senxor_thread._read_senxor()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is header
        assert result[1] is frame
        mock_senxor.read.assert_called_with(block=True, celsius=True)

        # Test when read returns None
        mock_senxor.read.return_value = (None, None)
        result = senxor_thread._read_senxor()
        assert result is None

    def test_add_remove_listener(self, senxor_thread):
        """Test adding and removing listeners."""
        # Create a test listener
        listener = MagicMock()

        # Add the listener
        with patch.object(senxor_thread._reader, "add_listener") as mock_add:
            mock_add.return_value = "test_listener"
            name = senxor_thread.add_listener(listener, "test_listener")
            assert name == "test_listener"

            # Check that the adapter function was created correctly
            adapter_fn = mock_add.call_args[0][0]
            test_data = (np.zeros(10), np.ones((32, 32)))
            adapter_fn(test_data)
            assert listener.call_count == 1
            call_args = listener.call_args[0]
            assert np.array_equal(call_args[0], test_data[0])
            assert np.array_equal(call_args[1], test_data[1])

            # Test with None data
            listener.reset_mock()
            adapter_fn(None)
            listener.assert_not_called()

        # Remove the listener
        with patch.object(senxor_thread._reader, "remove_listener") as mock_remove:
            senxor_thread.remove_listener("test_listener")
            mock_remove.assert_called_once_with("test_listener")

    def test_context_manager(self, senxor_thread):
        """Test using SenxorThread as a context manager."""
        with patch.object(senxor_thread, "start") as mock_start:
            with patch.object(senxor_thread, "stop") as mock_stop:
                with senxor_thread:
                    mock_start.assert_called_once()

                mock_stop.assert_called_once()

    def test_repr(self, senxor_thread):
        """Test the __repr__ method."""
        senxor_thread._senxor.address = "test_address"
        assert repr(senxor_thread) == "SenxorThread(addr='test_address')"

    def test_del(self, senxor_thread):
        """Test that __del__ calls stop."""
        with patch.object(senxor_thread, "stop") as mock_stop:
            senxor_thread.__del__()
            mock_stop.assert_called_once()

    def test_read_without_start(self, senxor_thread):
        """Test that read raises an error if the thread is not started."""
        with pytest.raises(RuntimeError, match="Thread not started"):
            senxor_thread.read()


class TestCVCamThread:
    @pytest.fixture
    def mock_capture(self):
        """Create a mock VideoCapture instance."""
        mock_instance = MagicMock()

        # Configure the mock to return test data
        mock_instance.read.return_value = (True, np.ones((480, 640, 3), dtype=np.uint8))
        mock_instance.isOpened.return_value = True
        mock_instance.get.side_effect = lambda prop: 640 if prop == 3 else 480 if prop == 4 else 0

        # Add an index attribute if possible
        mock_instance.index = 0

        return mock_instance

    @pytest.fixture
    def camera_thread(self, mock_capture):
        """Create a CVCamThread instance with a mock VideoCapture."""
        thread = CVCamThread(mock_capture)
        yield thread
        # Ensure cleanup
        if thread._started:
            thread.stop()

    def test_init(self, mock_capture):
        """Test that CVCamThread initializes correctly."""
        # Test with default parameters
        thread = CVCamThread(mock_capture)
        assert thread.camera_index == 0
        assert thread._started is False
        assert thread.cam is mock_capture

        # Test with custom parameters
        thread = CVCamThread(mock_capture, allow_listener=False)
        assert thread._reader._allow_listener is False
        assert thread.cam is mock_capture

        # Test with a capture that doesn't have an index attribute
        mock_capture_no_index = MagicMock()
        mock_capture_no_index.index = 0  # Explicitly set index to 0
        thread = CVCamThread(mock_capture_no_index)
        assert thread.camera_index == 0  # Should default to 0

    def test_read(self, camera_thread):
        """Test that read returns the correct data."""
        # Start the thread first to avoid RuntimeError
        camera_thread.start()

        # Test when no data is available
        with patch.object(camera_thread._reader, "read", return_value=None):
            success, frame = camera_thread.read()
            assert success is False
            assert frame is None

        # Test when data is available
        test_frame = np.ones((480, 640, 3), dtype=np.uint8)
        with patch.object(camera_thread._reader, "read", return_value=(True, test_frame)):
            success, frame = camera_thread.read()
            assert success is True
            assert np.array_equal(frame, test_frame)

    def test_start_stop(self, camera_thread, mock_capture):
        """Test that the thread starts and stops correctly."""
        # Test start
        with patch.object(camera_thread._reader, "start") as mock_reader_start:
            camera_thread.start()
            assert camera_thread._started is True
            mock_reader_start.assert_called_once()

        camera_thread.stop()
        assert camera_thread._started is False

        with patch.object(camera_thread._reader, "stop") as mock_reader_stop:
            camera_thread.stop()
            assert camera_thread._started is False
            mock_reader_stop.assert_not_called()

    def test_start_error_handling(self, camera_thread, mock_capture):
        """Test error handling during start."""
        mock_capture.isOpened.return_value = False

        with pytest.raises(RuntimeError, match="Camera is not open"):
            camera_thread.start()
        assert camera_thread._started is False

    def test_read_camera_method(self, camera_thread, mock_capture):
        """Test the camera reading functionality with different camera states."""
        # Test when camera is open
        mock_capture.isOpened.return_value = True
        camera_thread.start()

        # Test normal read
        test_frame = np.ones((480, 640, 3), dtype=np.uint8)
        mock_capture.read.return_value = (True, test_frame)
        result = camera_thread._read_camera()
        assert result is not None
        assert result[0] is True
        assert np.array_equal(result[1], test_frame)

        # Test failed read
        mock_capture.read.return_value = (False, None)
        result = camera_thread._read_camera()
        assert result is None

    def test_add_remove_listener(self, camera_thread):
        """Test adding and removing listeners."""
        listener = MagicMock()

        with patch.object(camera_thread._reader, "add_listener") as mock_add:
            mock_add.return_value = "test_listener"
            result = camera_thread.add_listener(listener, "test_listener")
            assert result == "test_listener"
            adapter_fn = mock_add.call_args[0][0]
            test_data = (True, np.ones((10, 10, 3)))
            adapter_fn(test_data)
            assert listener.call_count == 1
            call_args = listener.call_args[0]
            assert call_args[0] is True
            assert np.array_equal(call_args[1], np.ones((10, 10, 3)))

            listener.reset_mock()
            adapter_fn(None)
            listener.assert_not_called()

        with patch.object(camera_thread._reader, "remove_listener") as mock_remove:
            camera_thread.remove_listener("test_listener")
            mock_remove.assert_called_once_with("test_listener")

    def test_context_manager(self, camera_thread):
        """Test using CVCamThread as a context manager."""
        with patch.object(camera_thread, "start") as mock_start:
            with patch.object(camera_thread, "stop") as mock_stop:
                with camera_thread:
                    mock_start.assert_called_once()

                mock_stop.assert_called_once()

    def test_repr(self, camera_thread):
        """Test the __repr__ method."""
        assert repr(camera_thread) == "CVCamThread(camera_index=0)"

    def test_del(self, camera_thread):
        """Test that __del__ calls stop."""
        with patch.object(camera_thread, "stop") as mock_stop:
            camera_thread.__del__()
            mock_stop.assert_called_once()

    def test_read_without_start(self, camera_thread):
        """Test that read raises an error if the thread is not started."""
        with pytest.raises(RuntimeError, match="Thread not started"):
            camera_thread.read()
