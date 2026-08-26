with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\admin\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_api = "const API_BASE = 'http://127.0.0.1:8001';"
new_api = "// Use VITE_API_BASE from Vercel env, fallback to localhost\nconst API_BASE = typeof VITE_API_BASE !== 'undefined' ? VITE_API_BASE : 'http://127.0.0.1:8001';"

content = content.replace(old_api, new_api)

with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\admin\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed deployed admin portal API_BASE')