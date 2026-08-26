with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\customer\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hardcoded API_BASE line that overwrites window.API_BASE
content = content.replace(
    "var API_BASE = 'http://127.0.0.1:8001';",
    "// API_BASE is set via window.API_BASE at top of file"
)

with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\customer\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed customer portal hardcoded API_BASE')