/**
 * Deeply extracts text from an element, traversing through Shadow DOM roots recursively.
 * Useful for LINE Flex Messages (flex-renderer).
 * 
 * Usage in Playwright:
 * const text = await page.evaluate(getDeepText, element);
 */
function getDeepText(el) {
  if (!el) return "";
  let text = "";
  
  // 1. Check for Shadow Root
  if (el.shadowRoot) {
    text += getDeepText(el.shadowRoot);
  }
  
  // 2. Iterate through children (including Slot elements)
  for (const child of el.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      text += child.textContent + " ";
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      // Handle <slot> elements by looking at assigned nodes
      if (child.tagName === 'SLOT') {
        const assigned = child.assignedNodes();
        for (const node of assigned) {
          text += getDeepText(node);
        }
      } else {
        text += getDeepText(child);
      }
    }
  }
  
  return text;
}

// If using as a standalone snippet for page.evaluate:
// return Array.from(document.querySelectorAll('flex-renderer')).map(r => getDeepText(r));
