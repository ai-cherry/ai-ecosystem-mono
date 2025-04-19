"""
Banned words list for the PolicyGate.

This module provides a list of banned words that will be automatically
blocked by the PolicyGate when found in outgoing messages. This is implemented
as a simple "banned words" test that blocks messages containing specific strings.
"""

# Categories of banned words with associated terms
BANNED_CATEGORIES = {
    "profanity": [
        # Common profanity would be listed here
        # Placeholder entries for development/testing
        "profanity_placeholder_1",
        "profanity_placeholder_2",
    ],
    
    "hate_speech": [
        # Terms associated with hate speech would be listed here
        # Placeholder entries for development/testing
        "hate_speech_placeholder_1",
        "hate_speech_placeholder_2",
    ],
    
    "discrimination": [
        # Terms associated with discrimination would be listed here
        # Placeholder entries for development/testing
        "discrimination_placeholder_1",
        "discrimination_placeholder_2",
    ],
    
    "dangerous_content": [
        # Terms associated with dangerous activities would be listed here
        # Placeholder entries for development/testing
        "dangerous_content_placeholder_1",
        "dangerous_content_placeholder_2",
    ],
    
    "misinformation": [
        # Terms flagged as common misinformation markers would be listed here
        # Placeholder entries for development/testing
        "misinformation_placeholder_1",
        "misinformation_placeholder_2",
    ],
    
    "private_data": [
        # Terms that might indicate sharing of private data would be listed here
        # Placeholder entries for development/testing
        "private_data_placeholder_1",
        "private_data_placeholder_2",
    ]
}

# Testing placeholders
TEST_BANNED_WORDS = [
    "BANNED_WORD_TEST",
    "POLICY_VIOLATION_TEST",
    "HARMFUL_CONTENT_TEST"
]

# Flatten all categories into a single list for easy checking
BANNED_WORDS = []
for category, words in BANNED_CATEGORIES.items():
    BANNED_WORDS.extend(words)

# Add testing placeholders
BANNED_WORDS.extend(TEST_BANNED_WORDS)


def is_banned(text: str) -> bool:
    """
    Check if text contains any banned words.
    
    Args:
        text: The text to check
        
    Returns:
        True if text contains any banned word, False otherwise
    """
    if not text:
        return False
        
    # Convert to lowercase for case-insensitive comparison
    text_lower = text.lower()
    
    for word in BANNED_WORDS:
        if word.lower() in text_lower:
            return True
            
    return False


def get_banned_words_in_text(text: str) -> list:
    """
    Get all banned words found in the text.
    
    Args:
        text: The text to check
        
    Returns:
        List of banned words found in the text
    """
    if not text:
        return []
        
    # Convert to lowercase for case-insensitive comparison
    text_lower = text.lower()
    
    found = []
    for word in BANNED_WORDS:
        if word.lower() in text_lower:
            found.append(word)
            
    return found
