# `senxor.regmap.fields`

::: senxor.regmap.fields
    options:
      docstring_options:
        ignore_init_summary: true
      show_docstring_functions: false
      inherited_members: false
      show_symbol_type_heading: false
      show_symbol_type_toc: false
      parameter_headings: false
      show_bases: false
      show_signature: false

<style>
/*
  All styles are prefixed with .custom-fields-api to ensure
  they ONLY apply to this specific page and won't affect others.
*/

/* Hide the default messy attribute lists of nested classes */
.custom-fields-api .doc-class .doc-class .doc-children {
  display: none !important;
}

/* Custom card container for each Field class */
.custom-fields-api .field-card {
  border: 1px solid var(--md-typeset-table-color, #e0e0e0);
  border-radius: 8px;
  padding: 18px;
  margin-top: 16px;
  margin-bottom: 28px;
  background-color: var(--md-default-bg-color, #ffffff);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease;
}
.custom-fields-api .field-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Field description styling */
.custom-fields-api .field-description {
  font-size: 1.05em;
  margin-bottom: 14px;
  color: var(--md-typeset-color);
  line-height: 1.5;
}

/* Metadata grid for Address and Bits Range */
.custom-fields-api .field-meta-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.custom-fields-api .field-meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.custom-fields-api .meta-label {
  font-weight: 700;
  color: var(--md-typeset-color);
  opacity: 0.85;
  font-size: 0.9em;
}
.custom-fields-api .meta-value.code-style {
  font-family: var(--md-code-font-family, monospace);
  background-color: var(--md-code-bg-color, #f5f5f5);
  color: var(--md-code-fg-color);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.85em;
}

/* Status checkboxes container */
.custom-fields-api .field-flags {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.custom-fields-api .flag-checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85em;
  color: var(--md-typeset-color);
  user-select: none;
}
/* Custom checkbox styling following shadcn/ui design */
.custom-fields-api .checkbox-box {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--md-typeset-table-color, #cbd5e1);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.custom-fields-api .checkbox-box.checked {
  background-color: #3b82f6; /* Slate blue accent */
  border-color: #3b82f6;
  color: #ffffff;
}
.custom-fields-api .checkbox-box.unchecked {
  background-color: rgba(59, 130, 246, 0.04);
  border-color: var(--md-typeset-table-color, #cbd5e1);
}
.custom-fields-api .checkbox-box svg {
  width: 10px;
  height: 10px;
  fill: none;
  stroke: currentColor;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.custom-fields-api .flag-label {
  font-weight: 500;
  text-transform: lowercase;
}

/* Help information box - shadcn/ui Alert style */
.custom-fields-api .field-help-box {
  background-color: var(--md-code-bg-color, #f8fafc);
  border: 1px solid var(--md-typeset-table-color, #e2e8f0);
  padding: 14px 16px;
  border-radius: 8px;
  margin-top: 12px;
}
.custom-fields-api .help-title {
  font-weight: 600;
  margin-bottom: 6px;
  font-size: 0.85em;
  letter-spacing: 0.3px;
  color: var(--md-typeset-color);
  display: flex;
  align-items: center;
  gap: 6px;
}
.custom-fields-api .help-title svg {
  width: 14px;
  height: 14px;
  color: #3b82f6;
}
.custom-fields-api .help-content {
  white-space: pre-wrap;
  font-family: var(--md-typeset-font-family, inherit);
  line-height: 1.625;
  color: var(--md-typeset-color);
  opacity: 0.85;
  font-size: 0.9em;
}
</style>

<script>
(function() {
  function initCustomFields() {
    // Check if we are on the fields API page
    const h1 = document.querySelector('h1');
    if (!h1 || !h1.textContent.includes('senxor.regmap.fields')) {
      return;
    }

    // Add the scoping class to the article element
    const article = document.querySelector('article');
    if (article) {
      article.classList.add('custom-fields-api');
    }

    const classes = article.querySelectorAll('.doc-class');
    classes.forEach(cls => {
      // Check if this is a nested class.
      // A nested class is a .doc-class that is inside another .doc-class.
      const isNested = cls.parentElement && cls.parentElement.closest('.doc-class') !== null;
      if (!isNested) {
        return; // Skip the outer class (Fields)
      }

      // Avoid duplicate rendering during instant navigation
      if (cls.querySelector('.field-card')) return;

      const childrenContainer = cls.querySelector('.doc-children');
      if (!childrenContainer) return;

      const attributes = childrenContainer.querySelectorAll('.doc-attribute');
      const fieldData = {};

      attributes.forEach(attr => {
        // Prefer the code tag inside the attribute for clean signature extraction
        const heading = attr.querySelector('code') || attr.querySelector('.doc-heading') || attr;
        const headingClone = heading.cloneNode(true);

        // Remove labels to avoid polluting text content
        const labels = headingClone.querySelector('.doc-labels');
        if (labels) {
          labels.remove();
        }

        let text = headingClone.textContent.trim();

        // Remove trailing permalink symbol if present
        if (text.endsWith('¶')) {
          text = text.substring(0, text.length - 1).trim();
        }

        const eqIndex = text.indexOf('=');
        if (eqIndex === -1) return;

        const key = text.substring(0, eqIndex).trim();
        let val = text.substring(eqIndex + 1).trim();

        // Strip quotes/triple-quotes from string values
        if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) {
          val = val.substring(1, val.length - 1);
        }
        if (val.startsWith("'''") && val.endsWith("'''")) {
          val = val.substring(3, val.length - 3);
        }
        if (val.startsWith('"""') && val.endsWith('"""')) {
          val = val.substring(3, val.length - 3);
        }

        // Replace literal \n with actual newlines and clean docstring indentation
        if (key === 'help') {
          let rawLines = val.replace(/\\n/g, '\n').split('\n');
          if (rawLines.length > 1) {
            // Process lines starting from the second line (index 1)
            const processedLines = rawLines.map((line, idx) => {
              if (idx === 0) {
                return line; // Keep the first line untouched
              }
              // Strip leading spaces (up to 8 spaces to handle nested class docstring indentation)
              let cleanedLine = line;
              for (let i = 0; i < 8; i++) {
                if (cleanedLine.startsWith(' ')) {
                  cleanedLine = cleanedLine.substring(1);
                } else {
                  break;
                }
              }
              return cleanedLine;
            });
            val = processedLines.join('\n').trim();
          } else {
            val = val.trim();
          }
        }

        fieldData[key] = val;
      });

      if (Object.keys(fieldData).length > 0) {
        const card = document.createElement('div');
        card.className = 'field-card';

        // 1. Description
        if (fieldData.description) {
          const descDiv = document.createElement('div');
          descDiv.className = 'field-description';
          descDiv.innerHTML = `<strong>Description:</strong> ${escapeHtml(fieldData.description)}`;
          card.appendChild(descDiv);
        }

        // 2. Metadata Grid (Address & Bits Range)
        const metaGrid = document.createElement('div');
        metaGrid.className = 'field-meta-grid';

        if (fieldData.address !== undefined) {
          let addrStr = fieldData.address;
          const num = parseInt(fieldData.address);
          if (!isNaN(num)) {
            addrStr = `0x${num.toString(16).toUpperCase().padStart(2, '0')} (${num})`;
          }
          metaGrid.innerHTML += `
            <div class="field-meta-item">
              <span class="meta-label">Address:</span>
              <span class="meta-value code-style">${escapeHtml(addrStr)}</span>
            </div>
          `;
        }

        if (fieldData.bits_range) {
          metaGrid.innerHTML += `
            <div class="field-meta-item">
              <span class="meta-label">Bits Range:</span>
              <span class="meta-value code-style">${escapeHtml(fieldData.bits_range)}</span>
            </div>
          `;
        }

        if (metaGrid.children.length > 0) {
          card.appendChild(metaGrid);
        }

        // 3. Status Checkboxes (shadcn/ui style)
        const flagsDiv = document.createElement('div');
        flagsDiv.className = 'field-flags';

        const flags = ['writable', 'readable', 'self_reset'];
        flags.forEach(flag => {
          if (fieldData[flag] !== undefined) {
            const isTrue = fieldData[flag] === 'True';
            const label = flag.replace('_', ' ');

            const checkboxItem = document.createElement('div');
            checkboxItem.className = 'flag-checkbox-item';

            // Generate custom SVG checkbox
            checkboxItem.innerHTML = `
              <div class="checkbox-box ${isTrue ? 'checked' : 'unchecked'}">
                ${isTrue ? '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"></path></svg>' : ''}
              </div>
              <span class="flag-label">${escapeHtml(label)}</span>
            `;
            flagsDiv.appendChild(checkboxItem);
          }
        });

        if (flagsDiv.children.length > 0) {
          card.appendChild(flagsDiv);
        }

        // 4. Detailed Help Box (shadcn/ui Alert style)
        if (fieldData.help) {
          const helpBox = document.createElement('div');
          helpBox.className = 'field-help-box';
          helpBox.innerHTML = `
            <div class="help-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Help & Details</span>
            </div>
            <div class="help-content">${escapeHtml(fieldData.help)}</div>
          `;
          card.appendChild(helpBox);
        }

        const docContents = cls.querySelector('.doc-contents') || cls.querySelector('.doc-content') || cls;
        if (docContents) {
          docContents.appendChild(card);
        } else {
          cls.appendChild(card);
        }
      }
    });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Support both normal loading and Zensical/Material instant loading
  if (typeof document$ !== "undefined") {
    document$.subscribe(initCustomFields);
  } else {
    document.addEventListener("DOMContentLoaded", initCustomFields);
  }
})();
</script>
