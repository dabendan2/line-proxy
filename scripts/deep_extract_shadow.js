/**
 * Recursive function to extract all text content from a DOM element, 
 * including text hidden inside Shadow Roots.
 * 
 * Usage in Playwright:
 * const text = await page.evaluate(getDeepText, document.querySelector('flex-renderer'));
 */
function getDeepText(el) {
    let text = "";
    if (el.shadowRoot) {
        text += getDeepText(el.shadowRoot);
    }
    for (const child of el.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) {
            text += child.textContent + " ";
        } else if (child.nodeType === Node.ELEMENT_NODE) {
            text += getDeepText(child);
        }
    }
    return text;
}
