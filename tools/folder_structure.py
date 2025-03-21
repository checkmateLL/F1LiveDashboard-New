from pathlib import Path

def visualize_tree(path: Path, prefix: str = ''):
    print(prefix + path.name)
    if path.is_dir():
        for child in sorted(path.iterdir()):
            visualize_tree(child, prefix + '    ')

if __name__ == "__main__":
    import sys
    root_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    visualize_tree(root_path)