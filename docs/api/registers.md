# `senxor.regmap.registers`

::: senxor.regmap.registers
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
  All styles are prefixed with .custom-registers-api to ensure
  they ONLY apply to this specific page and won't affect others.
*/

/* Hide the default messy attribute lists of nested classes */
.custom-registers-api .doc-class .doc-class .doc-children {
  display: none !important;
}

/* Custom card container for each Register class */
.custom-registers-api .register-card {
  border: 1px solid var(--md-typeset-table-color, #e0e0e0);
  border-radius: 8px;
  padding: 18px;
  margin-top: 16px;
  margin-bottom: 28px;
  background-color: var(--md-default-bg-color, #ffffff);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease;
}
.custom-registers-api .register-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Register description styling */
.custom-registers-api .register-description {
  font-size: 1.05em;
  margin-bottom: 14px;
  color: var(--md-typeset-color);
  line-height: 1.5;
}

/* Metadata grid for Address */
.custom-registers-api .register-meta-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.custom-registers-api .register-meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.custom-registers-api .meta-label {
  font-weight: 700;
  color: var(--md-typeset-color);
  opacity: 0.85;
  font-size: 0.9em;
}
.custom-registers-api .meta-value.code-style {
  font-family: var(--md-code-font-family, monospace);
  background-color: var(--md-code-bg-color, #f5f5f5);
  color: var(--md-code-fg-color);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.85em;
}

/* Status checkboxes container */
.custom-registers-api .register-flags {
  display: flex;
  gap: 16px;
  margin-bottom: 0px;
  flex-wrap: wrap;
}
.custom-registers-api .flag-checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85em;
  color: var(--md-typeset-color);
  user-select: none;
}
/* Custom checkbox styling following shadcn/ui design */
.custom-registers-api .checkbox-box {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--md-typeset-table-color, #cbd5e1);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.custom-registers-api .checkbox-box.checked {
  background-color: #3b82f6; /* Slate blue accent */
  border-color: #3b82f6;
  color: #ffffff;
}
.custom-registers-api .checkbox-box.unchecked {
  background-color: rgba(59, 130, 246, 0.04);
  border-color: var(--md-typeset-table-color, #cbd5e1);
}
.custom-registers-api .checkbox-box svg {
  width: 10px;
  height: 10px;
  fill: none;
  stroke: currentColor;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.custom-registers-api .flag-label {
  font-weight: 500;
  text-transform: lowercase;
}
</style>

<script>
(function() {
  function initCustomRegisters() {
    // Check if we are on the registers API page
    const h1 = document.querySelector('h1');
    if (!h1 || !h1.textContent.includes('senxor.regmap.registers')) {
      return;
    }

    // Add the scoping class to the article element
    const article = document.querySelector('article');
    if (article) {
      article.classList.add('custom-registers-api');
    }

    const classes = article.querySelectorAll('.doc-class');
    classes.forEach(cls => {
      // Check if this is a nested class.
      // A nested class is a .doc-class that is inside another .doc-class.
      const isNested = cls.parentElement && cls.parentElement.closest('.doc-class') !== null;
      if (!isNested) {
        return; // Skip the outer class (Registers)
      }

      // Avoid duplicate rendering during instant navigation
      if (cls.querySelector('.register-card')) return;

      const childrenContainer = cls.querySelector('.doc-children');
      if (!childrenContainer) return;

      const attributes = childrenContainer.querySelectorAll('.doc-attribute');
      const registerData = {};

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

        registerData[key] = val;
      });

      if (Object.keys(registerData).length > 0) {
        const card = document.createElement('div');
        card.className = 'register-card';

        // 1. Description
        if (registerData.description) {
          const descDiv = document.createElement('div');
          descDiv.className = 'register-description';
          descDiv.innerHTML = `<strong>Description:</strong> ${escapeHtml(registerData.description)}`;
          card.appendChild(descDiv);
        }

        // 2. Metadata Grid (Address)
        const metaGrid = document.createElement('div');
        metaGrid.className = 'register-meta-grid';

        if (registerData.address !== undefined) {
          let addrStr = registerData.address;
          const num = parseInt(registerData.address);
          if (!isNaN(num)) {
            addrStr = `0x${num.toString(16).toUpperCase().padStart(2, '0')} (${num})`;
          }
          metaGrid.innerHTML += `
            <div class="register-meta-item">
              <span class="meta-label">Address:</span>
              <span class="meta-value code-style">${escapeHtml(addrStr)}</span>
            </div>
          `;
        }

        if (metaGrid.children.length > 0) {
          card.appendChild(metaGrid);
        }

        // 3. Status Checkboxes (shadcn/ui style)
        const flagsDiv = document.createElement('div');
        flagsDiv.className = 'register-flags';

        const flags = ['writable', 'readable', 'self_reset'];
        flags.forEach(flag => {
          if (registerData[flag] !== undefined) {
            const isTrue = registerData[flag] === 'True';
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
    document$.subscribe(initCustomRegisters);
  } else {
    document.addEventListener("DOMContentLoaded", initCustomRegisters);
  }
})();
</script>
