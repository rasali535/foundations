import os
import re
from pathlib import Path

def extract_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the pattern: Action: file_editor create <path> --file-text "<content>"
        # Note: The content might span multiple lines and contain escaped quotes.
        # This is a bit tricky with regex. Let's try a simpler approach of finding the start and end of the string.
        
        match = re.search(r'Action: file_editor (?:create|overwrite) (\S+) --file-text "(.*)"\s*Observation:', content, re.DOTALL)
        if match:
            target_path = match.group(1)
            actual_content = match.group(2)
            # Unescape double quotes and backslashes if needed, 
            # though usually the dump is literally what was written.
            # In the view_file output, I saw \" so they are escaped.
            actual_content = actual_content.replace('\\"', '"').replace('\\\\', '\\')
            return target_path, actual_content
        
        # Try another pattern if the above fails (e.g. no Observation)
        match = re.search(r'Action: file_editor (?:create|overwrite) (\S+) --file-text "(.*)"', content, re.DOTALL)
        if match:
            target_path = match.group(1)
            actual_content = match.group(2)
            # Find the last quote before any "Observation" or end of file
            # But the content itself might have quotes. 
            # Usually the AI block ends with " Observation:"
            if '"\nObservation:' in actual_content:
                actual_content = actual_content.split('"\nObservation:')[0]
            elif '"\r\nObservation:' in actual_content:
                actual_content = actual_content.split('"\r\nObservation:')[0]
            
            actual_content = actual_content.replace('\\"', '"').replace('\\\\', '\\')
            return target_path, actual_content

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return None, None

def main():
    root = Path('.')
    output_root = Path('foundations_app')
    
    for file in root.glob('*'):
        if file.is_file() and file.name not in ['extract.py', 'server.py', 'README.md', 'PMD.md', 'design_guidelines.json']:
            target_path_str, content = extract_content(file)
            if target_path_str and content:
                # Clean up target path (remove /app/ prefix)
                clean_path = target_path_str.replace('/app/', '')
                target_file = output_root / clean_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Extracted {file.name} to {target_file}")
        
        # Special case for server.py which is in the root and might be important
        if file.name == 'server.py':
             target_path_str, content = extract_content(file)
             if target_path_str and content:
                clean_path = target_path_str.replace('/app/', '')
                target_file = output_root / clean_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Extracted {file.name} to {target_file}")

if __name__ == "__main__":
    main()
