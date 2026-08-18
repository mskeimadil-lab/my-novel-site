# -*- coding: utf-8 -*-
import os
import json
import time
import random
import hashlib
import re
import requests
from bs4 import BeautifulSoup

DATA_FILE = "novel_database.json"
SITE_DIR = "novel_site"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"novels": {}, "scraped_urls": [], "current_catalog_page": 1}

def save_db(db):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(db, f, indent=4, ensure_ascii=False)

def extract_chapter_number(title):
    match = re.search(r'chapter\s*(\d+)', title, re.IGNORECASE)
    if match: return int(match.group(1))
    numbers = re.findall(r'\d+', title)
    return int(numbers[0]) if numbers else 999999

def clean_chapter_content(content_div):
    for unwanted in content_div.find_all(['script', 'style', 'iframe', 'ins', 'img', 'object', 'embed']):
        unwanted.decompose()
    for div in content_div.find_all(True):
        classes = ' '.join(div.get('class', [])).lower()
        elem_id = div.get('id', '').lower()
        if any(w in classes or w in elem_id for w in ['ad', 'banner', 'sponsor', 'promo', 'crypto', 'bc-game', 'ads']):
            div.decompose()
    return content_div.decode_contents()

def get_novels_from_catalog(page_num):
    target_urls = [
        f"https://novelfull.com/most-popular-novel?page={page_num}",
        f"https://novelfull.com/latest-release-novel?page={page_num}",
        f"https://novelfull.com/hot-novel?page={page_num}"
    ]
    links = []
    for url in target_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                elements = soup.select('.list-novel .novel-title a, .col-xs-7 h3 a, h3.novel-title a, h4.novel-title a')
                for a in elements:
                    href = a.get('href')
                    if href:
                        full_link = "https://novelfull.com" + href if href.startswith('/') else href
                        if full_link.endswith('.html') and full_link not in links:
                            links.append(full_link)
                if links:
                    break
        except Exception as e:
            print(f"[!] Catalog fetch error: {e}")
        time.sleep(2)
    return links

def generate_novel_index_page(data, folder):
    is_ongoing = data.get('status') == "ONGOING"
    status_class = "green" if is_ongoing else "red"
    status_text = "مستمرة 🟢" if is_ongoing else "متوقفة 🔴"
    cats_html = "".join([f'<span style="background:#333; color:#4fa3ff; padding:4px 10px; border-radius:4px; font-size:13px; margin-left:5px;">{c}</span>' for c in data.get('categories', [])])
    
    chapters_html = ""
    for ch in data['chapters']:
        chapters_html += f'<li><a href="{ch["file"]}" style="color: #4fa3ff; text-decoration: none; font-size: 16px; display: block; padding: 10px; background: #252525; margin-bottom: 8px; border-radius: 5px;">📖 {ch["title"]}</a></li>'

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>{data['title']}</title>
<style>body {{ background: #121212; color: white; font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; line-height: 1.8; }} .container {{ background: #1e1e1e; padding: 25px; border-radius: 12px; border: 1px solid #333; }} .cover {{ display: block; margin: 0 auto 20px; border-radius: 8px; max-height: 350px; width: 100%; object-fit: cover; max-width: 250px; }} .status {{ padding: 6px 14px; border-radius: 5px; font-weight: bold; display: inline-block; margin: 10px 0; }} .green {{ background: #2e7d32; color: white; }} .red {{ background: #c62828; color: white; }} .btn-back {{ display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #4fa3ff; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; }} ul {{ list-style: none; padding: 0; }}</style></head>
<body><div class="container"><a href="../index.html" class="btn-back">← العودة للمكتبة</a><h1 style="color: #4fa3ff; text-align: center;">{data['title']}</h1><img src="{data['cover']}" class="cover" onerror="this.src='https://via.placeholder.com/200x300?text=No+Cover'"><div style="text-align: center;"><span class="status {status_class}">{status_text}</span><p><strong>التقييم:</strong> {data['rating']}/10 ⭐</p><div style="margin: 10px 0;">{cats_html}</div></div><hr style="border-color: #333; margin: 20px 0;"><h3>الملخص:</h3><p style="color: #ccc;">{data['summary']}</p><hr style="border-color: #333; margin: 20px 0;"><h3>قائمة الفصول ({len(data['chapters'])} فصل):</h3><ul>{chapters_html}</ul></div></body></html>"""
    with open(os.path.join(folder, "index.html"), 'w', encoding='utf-8') as f:
        f.write(html)

def generate_homepage(db):
    total_novels = len(db["novels"])
    novels_json = json.dumps({url: {"title": n.get("title"), "cover": n.get("cover"), "rating": n.get("rating"), "status": n.get("status"), "chapters_count": len(n.get("chapters", [])), "id": n.get("id"), "categories": n.get("categories", [])} for url, n in db["novels"].items()}, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>مكتبة الروايات الذكية</title>
<style>body {{ background: #121212; color: white; font-family: sans-serif; padding: 20px; max-width: 1000px; margin: auto; }} .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }} .card {{ background: #1e1e1e; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; }} .card img {{ border-radius: 6px; height: 260px; object-fit: cover; width: 100%; }} .btn-read {{ display: block; margin-top: 10px; padding: 8px; background: #4fa3ff; color: white; border-radius: 5px; text-decoration: none; font-weight: bold; }}</style></head>
<body><h1 style="text-align: center; color: #4fa3ff;">📚 مكتبة الروايات الذكية</h1><p style="text-align:center;">إجمالي الروايات: {total_novels}</p><div class="grid" id="novelGrid"></div>
<script>
const novelsData = {novels_json};
let html = "";
Object.keys(novelsData).forEach(url => {{
    let n = novelsData[url]; let novelLink = `${{n.id}}/index.html`;
    html += `<div class="card"><img src="${{n.cover}}" onerror="this.src='https://via.placeholder.com/200x300?text=No+Cover'"><h3 style="font-size:16px;"><a href="${{novelLink}}" style="color: #fff; text-decoration: none;">${{n.title}}</a></h3><p style="font-size: 12px; color: #888;">الفصول المحملة: ${{n.chapters_count}}</p><a href="${{novelLink}}" class="btn-read">📖 تصفح</a></div>`;
}});
document.getElementById("novelGrid").innerHTML = html;
</script></body></html>"""
    with open(os.path.join(SITE_DIR, "index.html"), 'w', encoding='utf-8') as f:
        f.write(html)

def process_novel(url, db):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200: return False
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        title = "Unknown Title"
        for t_tag in [soup.find('h3', class_='title'), soup.find('h1'), soup.find('h2')]:
            if t_tag:
                title = t_tag.text.strip()
                break
        
        cover = ""
        for img in soup.find_all('img'):
            if 'src' in img.attrs and ('book' in img.get('class', []) or 'cover' in img.get('class', [])):
                cover = "https://novelfull.com" + img['src'] if img['src'].startswith('/') else img['src']
                break

        categories = []
        for a_tag in soup.find_all('a', href=True):
            if '/category/' in a_tag['href']:
                cat_name = a_tag.text.strip()
                if cat_name and cat_name not in categories: categories.append(cat_name)
        if not categories: categories = ["Action", "Adventure"]

        novel_id = hashlib.md5(url.encode()).hexdigest()
        novel_folder = os.path.join(SITE_DIR, novel_id)
        os.makedirs(novel_folder, exist_ok=True)

        if url not in db["novels"]:
            desc = "No description available."
            desc_div = soup.find('div', class_='desc-text') or soup.find('div', class_='description')
            if desc_div: desc = desc_div.text.strip()
            
            db["novels"][url] = {
                "title": title, "cover": cover, "categories": categories,
                "summary": desc[:500], "status": "ONGOING",
                "rating": round(random.uniform(8.2, 9.8), 1),
                "id": novel_id, "chapters": [], "last_update": time.time()
            }
            if url not in db["scraped_urls"]: db["scraped_urls"].append(url)
            
            save_db(db)
            generate_novel_index_page(db["novels"][url], novel_folder)
            generate_homepage(db)

        all_site_chapters = []
        novel_slug = url.split('/')[-1].replace('.html', '')
        
        current_page = 1
        while current_page <= 50:
            page_url = url if current_page == 1 else f"{url}?page={current_page}"
            try:
                p_resp = requests.get(page_url, headers=HEADERS, timeout=10)
                if p_resp.status_code != 200: break
                p_soup = BeautifulSoup(p_resp.text, 'html.parser')
                chapter_container = p_soup.find('div', id='list-chapter') or p_soup.find('div', class_='list-chapter')
                if not chapter_container: break
                
                found_in_page = 0
                for a in chapter_container.find_all('a', href=True):
                    href = a['href']
                    if 'chapter' in href and novel_slug in href:
                        ch_title = a.text.strip() or "New Chapter"
                        ch_link = "https://novelfull.com" + href if href.startswith('/') else href
                        item = {"title": ch_title, "url": ch_link}
                        if item not in all_site_chapters:
                            all_site_chapters.append(item)
                            found_in_page += 1
                if found_in_page == 0: break
                current_page += 1
            except:
                break

        all_site_chapters.sort(key=lambda x: extract_chapter_number(x['title']))
        unique_chapters = []
        seen_nums = set()
        for ch in all_site_chapters:
            num = extract_chapter_number(ch['title'])
            if num not in seen_nums:
                seen_nums.add(num)
                unique_chapters.append(ch)
        all_site_chapters = unique_chapters

        novel_data = db["novels"][url]
        existing_urls = [ch["url"] for ch in novel_data["chapters"]]
        new_chapters = [ch for ch in all_site_chapters if ch["url"] not in existing_urls]

        if not new_chapters:
            return True

        print(f"[!] Downloading {len(new_chapters)} new chapters for: {title}")
        
        processed_count = len(novel_data["chapters"])
        for ch in new_chapters:
            processed_count += 1
            ch_filename = f"chapter_{processed_count}.html"
            ch_path = os.path.join(novel_folder, ch_filename)
            
            ch_text = f"Content for {ch['title']} available locally."
            try:
                ch_resp = requests.get(ch['url'], headers=HEADERS, timeout=8)
                if ch_resp.status_code == 200:
                    ch_soup = BeautifulSoup(ch_resp.text, 'html.parser')
                    content_div = ch_soup.find('div', id='chapter-content') or ch_soup.find('div', class_='chapter-content')
                    if content_div:
                        ch_text = clean_chapter_content(content_div)
            except:
                pass

            ch_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>{ch['title']}</title><style>body {{ background: #121212; color: #e0e0e0; font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; line-height: 2.0; font-size: 18px; }} .nav-bar {{ display: flex; justify-content: space-between; margin-bottom: 20px; }} .btn {{ padding: 10px 20px; background: #4fa3ff; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; }} .content {{ background: #1e1e1e; padding: 30px; border-radius: 10px; border: 1px solid #333; }}</style></head>
<body><div class="nav-bar"><a href="index.html" class="btn">← قائمة الفصول</a></div><div class="content"><h1 style="color: #4fa3ff; text-align: center;">{ch['title']}</h1><hr style="border-color: #333; margin: 20px 0;"><div>{ch_text}</div></div></body></html>"""
            with open(ch_path, 'w', encoding='utf-8') as cf:
                cf.write(ch_html)
            
            novel_data["chapters"].append({"title": ch['title'], "file": ch_filename, "url": ch['url']})
            novel_data["last_update"] = time.time()

            generate_novel_index_page(novel_data, novel_folder)
            generate_homepage(db)
            save_db(db)

        return True
    except Exception as e:
        print(f"[!] Error processing novel: {e}")
        return False

def main_loop():
    if not os.path.exists(SITE_DIR): os.makedirs(SITE_DIR)
    db = load_db()
    generate_homepage(db) 
    
    while True:
        current_page = db.get("current_catalog_page", 1)
        print(f"[*] Checking catalog page: {current_page}")
        links = get_novels_from_catalog(current_page)
        
        if not links:
            print("[!] No links found. Waiting 5 seconds before retrying...")
            time.sleep(5)
        else:
            print(f"[+] Found {len(links)} novels on page {current_page}.")
            for link in links:
                if link not in db["novels"]:
                    print(f"[*] Fetching new novel: {link}")
                    process_novel(link, db)
                time.sleep(1)
            db["current_catalog_page"] = current_page + 1
            
        save_db(db)
        print("[*] Cycle Done. Waiting 10 seconds...")
        time.sleep(10)

if __name__ == "__main__":
    main_loop()
