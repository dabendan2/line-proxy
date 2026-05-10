/**
 * find_line_contact.js
 * 
 * Robustly finds and clicks a LINE contact in the search results sidebar.
 * Uses recursive Shadow DOM traversal to find elements hidden from standard DOM queries.
 * Prioritizes individual friends over groups by checking for the "Friends" section.
 * 
 * @param {string} targetName - The display name to look for.
 * @returns {string} - Status of the search/click operation.
 */
async (targetName) => {
    function findElementsContainingText(root, text, results = []) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while (node = walker.nextNode()) {
            if (node.textContent.includes(text)) {
                results.push(node.parentElement);
            }
        }
        const allElements = root.querySelectorAll('*');
        for (const el of allElements) {
            if (el.shadowRoot) {
                findElementsContainingText(el.shadowRoot, text, results);
            }
        }
        return results;
    }

    function findButtonByText(root, texts) {
        const elements = Array.from(root.querySelectorAll('button, [role="button"], span, div'));
        for (const el of elements) {
            if (texts.some(t => el.innerText && el.innerText.includes(t))) {
                return el;
            }
        }
        const allElements = root.querySelectorAll('*');
        for (const el of allElements) {
            if (el.shadowRoot) {
                const found = findButtonByText(el.shadowRoot, texts);
                if (found) return found;
            }
        }
        return null;
    }

    // 1. Prioritize elements under "Friends" or "好友" header
    const candidates = findElementsContainingText(document, targetName);
    const friendsHeaders = findElementsContainingText(document, "Friends").concat(findElementsContainingText(document, "好友"))
        .filter(el => el.innerText === "Friends" || el.innerText === "好友");

    let targetElement = null;
    
    if (friendsHeaders.length > 0) {
        const friendsHeader = friendsHeaders[0];
        const headerRect = friendsHeader.getBoundingClientRect();
        targetElement = candidates.find(el => {
            const rect = el.getBoundingClientRect();
            return rect.top > headerRect.top && rect.left < 400;
        });
    }

    // Fallback: pick the best candidate (usually in the sidebar)
    if (!targetElement) {
        targetElement = candidates.find(el => el.getBoundingClientRect().left < 400);
    }

    if (targetElement) {
        targetElement.click();
        // Wait briefly for potential profile transition
        await new Promise(r => setTimeout(r, 1500));
        
        // 2. Check for "Chat" or "聊天" button in case a profile overlay opened
        const chatBtn = findButtonByText(document, ["Chat", "聊天"]);
        if (chatBtn) {
            chatBtn.click();
            return "clicked_chat_button_in_profile";
        }
        return "clicked_contact_directly";
    }

    return "not_found";
}
