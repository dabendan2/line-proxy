() => {
    const getDeepText = (el) => {
        let text = "";
        if (el.shadowRoot) text += getDeepText(el.shadowRoot);
        for (const child of el.childNodes) {
            text += child.textContent + " ";
            if (child.nodeType === Node.ELEMENT_NODE) text += getDeepText(child);
        }
        return text.trim();
    };
    const msgElements = document.querySelectorAll('span[data-message-content], .message_text, flex-renderer');
    return Array.from(msgElements).map(el => ({
        text: getDeepText(el),
        is_self_dom: el.closest('.mdNM08MsgSelf') !== null || el.closest('[class*="Self"]') !== null
    }));
}
