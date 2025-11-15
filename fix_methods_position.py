"""
Fix methods position - move methods inside MainWindow class
"""

# Read the file
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the methods that were added outside the class
methods_start = -1
methods_end = -1
for i, line in enumerate(lines):
    if '    # ============================================' in line and i > 2500:
        if '# Story Management Methods' in lines[i+1]:
            methods_start = i
    if methods_start > 0 and 'if __name__ ==' in line:
        methods_end = i
        break

if methods_start > 0 and methods_end > 0:
    # Extract the methods
    methods_lines = lines[methods_start:methods_end]

    # Remove the methods from their current position
    del lines[methods_start:methods_end]

    # Find where to insert them (before def main():)
    insert_position = -1
    for i, line in enumerate(lines):
        if 'def main():' in line and i > 2000:
            insert_position = i
            break

    if insert_position > 0:
        # Insert the methods before main()
        for j, method_line in enumerate(methods_lines):
            lines.insert(insert_position + j, method_line)

        print("✅ Successfully moved methods inside MainWindow class!")
        print(f"Methods moved from line ~{methods_start} to line ~{insert_position}")
    else:
        print("❌ Could not find main() function")
else:
    print("❌ Could not find methods to move")

# Write the file
with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
