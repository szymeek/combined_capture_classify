import os
import sys

def rename_files_in_folder(folder_path, base_name):
    """
    Rename all files in a folder with a base name and sequential numbers.
    
    Args:
        folder_path (str): Path to the folder containing files to rename
        base_name (str): Base name for the renamed files
    """
    try:
        # Check if folder exists
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' does not exist.")
            return False
        
        # Get all files (not directories) from the folder
        all_items = os.listdir(folder_path)
        files = [f for f in all_items if os.path.isfile(os.path.join(folder_path, f))]
        
        if not files:
            print("No files found in the specified folder.")
            return False
        
        # Sort files alphabetically for consistent ordering
        files.sort()
        
        print(f"Found {len(files)} file(s) to rename:")
        for i, filename in enumerate(files, start=1):
            print(f"  {i}. {filename}")
        
        # Confirm before proceeding
        confirm = input(f"\nProceed with renaming {len(files)} files? (y/N): ").lower()
        if confirm not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
        
        # Rename each file
        renamed_count = 0
        for i, filename in enumerate(files, start=1):
            # Get the file extension
            file_name, file_ext = os.path.splitext(filename)
            
            # Create new filename with 3-digit zero-padded number
            new_name = f"{base_name}{i:03d}{file_ext}"
            
            # Full paths
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_name)
            
            # Check if new filename already exists
            if os.path.exists(new_path) and old_path != new_path:
                print(f"Warning: File '{new_name}' already exists. Skipping '{filename}'.")
                continue
            
            try:
                # Rename the file
                os.rename(old_path, new_path)
                print(f"Renamed: '{filename}' -> '{new_name}'")
                renamed_count += 1
            except OSError as e:
                print(f"Error renaming '{filename}': {e}")
        
        print(f"\nSuccessfully renamed {renamed_count} out of {len(files)} files.")
        return True
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def main():
    """Main function to get user input and execute file renaming."""
    print("=== File Batch Renamer ===")
    print("This script renames all files in a folder with a base name + sequential numbers (001, 002, etc.)")
    print("File extensions are preserved.\n")
    
    # Get folder path
    while True:
        folder_path = input("Enter the folder path (or 'q' to quit): ").strip()
        
        if folder_path.lower() == 'q':
            print("Goodbye!")
            sys.exit(0)
        
        # Handle relative paths and current directory
        if folder_path == '.' or folder_path == '':
            folder_path = os.getcwd()
            print(f"Using current directory: {folder_path}")
        else:
            folder_path = os.path.abspath(folder_path)
        
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            break
        else:
            print(f"Error: '{folder_path}' is not a valid directory. Please try again.\n")
    
    # Get base name
    while True:
        base_name = input("\nEnter the base name for files (e.g., 'test' for test001, test002, etc.): ").strip()
        
        if not base_name:
            print("Base name cannot be empty. Please try again.")
            continue
        
        # Check for invalid characters in filename
        invalid_chars = '<>:"/\\|?*'
        if any(char in base_name for char in invalid_chars):
            print(f"Base name contains invalid characters: {invalid_chars}")
            print("Please use a different base name.")
            continue
        
        break
    
    # Execute renaming
    print(f"\nProcessing folder: {folder_path}")
    print(f"Base name: {base_name}")
    rename_files_in_folder(folder_path, base_name)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        input("Press Enter to exit...")
