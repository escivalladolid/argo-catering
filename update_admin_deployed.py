with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\admin\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_brand_css = """ .brand{display:flex;align-items:center;gap:10px;padding:8px 8px 18px;}
.brand-icon{width:44px;height:44px;border-radius:14px;background:linear-gradient(160deg,var(--blue) 0%,var(--blue-deep) 100%);display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;flex-shrink:0;box-shadow:0 14px 30px -10px rgba(29,78,216,0.45);}
.brand-name{color:#fff;font-size:14px;font-weight:700;}"""

new_brand_css = """ .brand{display:flex;flex-direction:column;align-items:center;gap:16px;padding:24px 12px 32px;text-align:center;}
.brand-badge{width:84px;height:84px;border-radius:22px;background:linear-gradient(160deg,var(--blue) 0%,var(--blue-deep) 100%);display:flex;align-items:center;justify-content:center;box-shadow:0 14px 30px -10px rgba(29,78,216,0.45);margin:0 auto;}
.brand-badge svg{width:44px;height:44px;}
.brand-name{font-size:clamp(28px,8vw,48px);font-weight:900;letter-spacing:-0.03em;line-height:1;color:#fff;}
.brand-name span{color:var(--blue);}
.brand-tag{margin-top:8px;font-size:12px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:var(--blue);}"""

content = content.replace(old_brand_css, new_brand_css)

old_brand_html = '<div class="brand">\n      <div class="brand-icon"><i class="bi bi-utensils"></i></div>\n      <div class="brand-name">Catering Management System</div>\n    </div>'

new_brand_html = '''<div class="brand">
      <div class="brand-badge">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 3C7.5 3 4 6.5 4 11H20C20 6.5 16.5 3 12 3Z" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="M2.5 11H21.5" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M12 3V1.4" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M4.5 14.5H19.5" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="brand-name">ARG<span>O</span></div>
      <div class="brand-tag">Catering Management System</div>
    </div>'''

content = content.replace(old_brand_html, new_brand_html)

with open(r'C:\xampp\htdocs\Capstone-Mobile-Quiz-System\admin\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated deployed admin portal')