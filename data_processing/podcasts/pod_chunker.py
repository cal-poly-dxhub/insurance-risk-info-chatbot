def sliding_window_chunker(text, window_size=50, overlap=10):
    """
    Splits the input text into chunks using a sliding window approach based on word count.

    Args:
    - text (str): The input text to be chunked.
    - window_size (int): The size of each chunk in number of words.
    - overlap (int): The number of words that overlap between consecutive chunks.

    Returns:
    - List[str]: A list of text chunks.
    """
    # Split the text into words using spaces as the delimiter
    words = text.split()
    
    # Initialize the list to hold chunks
    chunks = []
    
    # Calculate the step size (window_size - overlap)
    step = window_size - overlap
    
    # Iterate over the words to generate chunks
    for i in range(0, len(words), step):
        # Extract words for the current chunk
        chunk_words = words[i:i + window_size]
        # Convert the list of words back into a single string
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        # Break the loop if the last chunk is reached and it's smaller than the window size
        if len(chunk_words) < window_size:
            break
    
    return chunks

with open('transcript.txt', "r", encoding="utf-8") as file:
    text = file.read()

# Call the function with example text
chunks = sliding_window_chunker(text, window_size=300, overlap=50)
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:\n{chunk}\n")
