/* Shared, local-only LaTeX presentation. Never interpret model output as HTML. */
(() => {
  'use strict';
  const sources = new WeakMap();
  const ignored = 'script,style,noscript,textarea,input,select,option,pre,code,a,.katex,.katex-display';
  const delimiters = [
    {left: '$$', right: '$$', display: true},
    {left: '\\[', right: '\\]', display: true},
    {left: '\\(', right: '\\)', display: false},
    ...['equation', 'equation*', 'align', 'align*', 'gather', 'gather*', 'aligned'].map(name => ({
      left: `\\begin{${name}}`, right: `\\end{${name}}`, display: true,
    })),
  ];

  function render(container) {
    if (!container || container.matches(ignored) || !window.renderMathInElement) return;
    container.classList.add('math-content');
    // Accept inline $x^2$ as well, without treating prices such as "$10 and $20"
    // or escaped dollars as formulas. Code blocks and editing fields stay literal.
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.parentElement.closest(ignored) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      node.nodeValue = node.nodeValue.replace(/(?<![\\$])\$(?![\s$])([^$\r\n]+?)(?<![\\\s])\$(?!\$)/g,
        (_, math) => `\\(${math}\\)`);
    }
    window.renderMathInElement(container, {
      delimiters,
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'input', 'select', 'option', 'pre', 'code', 'a'],
      ignoredClasses: ['katex', 'katex-display'],
      // No external images/links/HTML extensions, unbounded sizes or recursive macros.
      trust: false, maxSize: 10, maxExpand: 1000, strict: 'ignore',
      throwOnError: true,
      // A malformed AI formula remains readable source; other formulas still render.
      errorCallback: () => {},
    });
  }

  function setText(container, value) {
    if (!container) return;
    const raw = String(value ?? '');
    sources.set(container, raw);
    container.textContent = raw;
    render(container);
  }

  // Saving progress must use the original LaTeX, not KaTeX's duplicated
  // visual + screen-reader text. Answers and server-side grading are unchanged.
  function source(container) { return sources.get(container) ?? container?.textContent ?? ''; }

  function feedbackLines(raw) {
    // Keep multiline display/inline formulas in one DOM node while retaining
    // the existing Result / Reference answer / Brief explanation styling.
    return String(raw).match(/(?:\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([\s\S]*?\\\)|\\begin\{([a-z*]+)\}[\s\S]*?\\end\{\1\}|[^\r\n])+/g) || [];
  }

  window.mathUI = {render, setText, source, feedbackLines};
})();
