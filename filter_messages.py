import re

# Basic Dutch stopwords, extend if needed
dutch_stopwords = set("""
de het en een van ik je niet dat die
""".split())

# Basic English stopwords, extend if needed
english_stopwords = set("""
the and is in you not that it on for
""".split())

def is_mostly_dutch(text, threshold=0.5):
    words = re.findall(r'\b\w+\b', text.lower())
    dutch_count = sum(1 for w in words if w in dutch_stopwords)
    eng_count = sum(1 for w in words if w in english_stopwords)
    total = dutch_count + eng_count
    if total == 0:
        return False  # no stopwords, keep message
    ratio = dutch_count / total
    return ratio > threshold

def is_gibberish(text):
    if len(re.findall(r'[a-zA-Z]', text)) < 3:
        return True
    letter_count = sum(c.isalpha() for c in text)
    if letter_count / max(len(text), 1) < 0.5:
        return True
    if re.fullmatch(r'(.)\1{3,}', text):
        return True
    return False

def filter_messages(input_file, output_file):
    with open(input_file, encoding='utf-8') as fin, open(output_file, 'w', encoding='utf-8') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            if is_mostly_dutch(line):
                continue
            if is_gibberish(line):
                continue
            fout.write(line + '\n')

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 filter_messages.py input.txt output.txt")
        sys.exit(1)
    filter_messages(sys.argv[1], sys.argv[2])
    print(f"Filtered messages written to {sys.argv[2]}")
