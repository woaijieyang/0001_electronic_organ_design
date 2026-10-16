"""Build local/offline HTML from the canonical Markdown and preserved source."""
from pathlib import Path
import re,html,json,hashlib
import markdown
from pygments import lex
from pygments.lexers import CLexer
from pygments.token import Comment, Keyword, String, Number, Name
from bs4 import BeautifulSoup
from build_appendix import read,build
R=Path(__file__).resolve().parents[1]
NAME='电子琴设计_技术文档'
def code_name(rel):return rel.replace('/','--')+'.html'
def colored_lines(txt):
 lines=['']
 for token,value in lex(txt,CLexer(stripnl=False,ensurenl=False)):
  cls='syntax-comment' if token in Comment else 'syntax-keyword' if token in Keyword else 'syntax-string' if token in String else 'syntax-number' if token in Number else 'syntax-function' if token in Name.Function else ''
  for n,part in enumerate(value.split('\n')):
   if n:lines.append('')
   if part:lines[-1]+=f'<span class="{cls}">{html.escape(part)}</span>' if cls else html.escape(part)
 if txt.endswith('\n'):lines.pop()
 return ''.join(f'<span class="code-line" id="L{i}"><a class="line-no" href="#L{i}">{i}</a>{line}</span>' for i,line in enumerate(lines,1))
def shell(title,body,extra='',prefix=''):
 version=hashlib.sha256((R/'assets/styles/showcase.css').read_bytes()).hexdigest()[:10]
 return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="从一次琴键按下，到双通道声音、六种伴奏与完整交互：STM32电子琴的程序设计、参数解释与调试方法。"><link rel="stylesheet" href="{prefix}assets/styles/document.css"><link rel="stylesheet" href="{prefix}assets/styles/showcase.css?v={version}">{extra}</head><body>{body}</body></html>'''
def top(prefix=''):
 return f'''<header class="topbar"><a class="brand" href="{prefix}index.html"><img class="seal" src="{prefix}assets/photos/sdu-emblem.png" alt="山东大学校徽" width="42" height="42"><span><strong>山东大学</strong><small>SHANDONG UNIVERSITY</small></span></a><nav class="top-actions"><a href="{prefix}index.html">项目首页</a><a href="{prefix}{NAME}.md" class="desktop-only">Markdown</a><a href="{prefix}{NAME}.html#chapter-10">演示与复现</a></nav></header><div class="progress"></div>'''
def hero(home=False):
 return f'''<section class="hero {'home-hero' if home else ''}"><div class="hero-inner"><div class="eyebrow">EMBEDDED SYSTEMS · A PROJECT FROM 2024</div><h1>{NAME.replace('_',' · ')}</h1><p>七个琴键、六种伴奏，以及把它们接在一起的程序。</p></div></section>'''
def footer():return '''<footer class="footer">山东大学 · 电子琴设计</footer>'''
def main():
 build()
 source=(R/(NAME+'.md')).read_text(encoding='utf-8')
 body=markdown.markdown(source,extensions=['tables','fenced_code','toc','sane_lists','codehilite'],extension_configs={'toc':{'permalink':False},'codehilite':{'guess_lang':False,'css_class':'code-highlight'}})
 soup=BeautifulSoup(body,'html.parser');soup.h1.decompose()
 # Explicit stable anchors are the same in Markdown and HTML.
 for a in soup.select('a[id]'):
  h=a.find_next('h2')
  if h:
   h['id']=a['id'];parent=a.parent;a.decompose()
   if parent.name=='p' and not parent.get_text(strip=True):parent.decompose()
 headings=[(h['id'],h.get_text(' ',strip=True)) for h in soup.find_all('h2')]
 nav='<ul>'+''.join(f'<li><a href="#{html.escape(i)}">{html.escape(t)}</a></li>' for i,t in headings)+'</ul>'
 for table in soup.find_all('table'):
  w=soup.new_tag('div',attrs={'class':'table-wrap','tabindex':'0','role':'region','aria-label':'可横向滚动的参数表'});table.wrap(w)
 # Native images render offline; same source files also work in GitHub Markdown.
 for img in soup.find_all('img'):
  img['loading']='eager';img['decoding']='async'
 for a in soup.select('a[href]'):
  href=a['href']
  if href.startswith('firmware/') and re.search(r'\.(c|h|s)(#L\d+)?$',href,re.I):
   rel,sep,frag=href[len('firmware/'):].partition('#')
   a['href']='code/'+code_name(rel)+(('#'+frag) if sep else '')
  elif href.startswith('http'):a['target']='_blank';a['rel']='noopener noreferrer'
 # Wrap the opening and reading map without changing their text.
 h2=soup.find('h2');section=soup.new_tag('section',attrs={'class':'overview'})
 h2.insert_before(section);node=h2
 while node and (node==h2 or node.name!='h2'):
  nxt=node.next_sibling;section.append(node.extract());node=nxt
 nav_h=soup.find('h2',string='阅读导航')
 if nav_h:
  wrap=soup.new_tag('section',attrs={'class':'nav-inline'});nav_h.insert_before(wrap);node=nav_h
  while node and (node==nav_h or node.name!='h2'):
   nxt=node.next_sibling;wrap.append(node.extract());node=nxt
 # Appendices remain fully present; collapse by category for comfortable browsing.
 app=soup.find(id='appendix')
 toolbar=soup.new_tag('div',attrs={'class':'appendix-toolbar'})
 toolbar.append('参数速查')
 btn=soup.new_tag('button',attrs={'type':'button','data-expand':''});btn.string='展开全部附录';toolbar.append(btn)
 app.insert_after(toolbar)
 for h in list(soup.find_all('h3')):
  if not re.match(r'^[A-G]\. ',h.get_text()):continue
  detail=soup.new_tag('details',attrs={'class':'appendix-block'});summary=soup.new_tag('summary');summary.string=h.get_text();detail.append(summary)
  content=soup.new_tag('div',attrs={'class':'appendix-content'});detail.append(content);h.insert_before(detail)
  oldid=h.get('id');detail['id']=oldid
  node=h.next_sibling;h.decompose()
  while node and node.name not in ('h2','h3'):
   nxt=node.next_sibling;content.append(node.extract());node=nxt
 # Replace poster paragraphs with players while keeping captions and links.
 for img in list(soup.find_all('img')):
  src=img.get('src','')
  if src.endswith(('short-poster.jpg','full-poster.jpg')):
   kind='short' if 'short-' in src else 'full';wrap=soup.new_tag('div',attrs={'class':'video-block'})
   video=soup.new_tag('video',attrs={'controls':'','preload':'metadata','playsinline':'','poster':src})
   so=soup.new_tag('source',attrs={'src':f'assets/video/demo-{kind}.mp4','type':'video/mp4'});video.append(so)
   video.append('浏览器不支持内嵌视频，请使用下方观看链接。');wrap.append(video)
   img.parent.replace_with(wrap)
 mobile=BeautifulSoup(f'<details class="mobile-nav"><summary>阅读目录</summary><nav>{nav}</nav></details>','html.parser')
 soup.select_one('.overview').insert_after(mobile)
 article=str(soup)
 layout=f'<div class="layout"><aside class="sidebar"><div class="toc-label">CONTENTS / 阅读路径</div>{nav}</aside><main><article class="article">{article}</article></main></div>'
 doc=shell(NAME,top()+hero()+layout+footer()+'<button class="to-top" aria-label="返回顶部">↑</button><script src="assets/styles/document.js"></script>')
 (R/(NAME+'.html')).write_text(doc,encoding='utf-8')
 # Readable, linked source mirror. Original firmware remains byte-identical.
 for p in (R/'firmware').rglob('*'):
  if p.suffix.lower() not in ('.c','.h','.s'):continue
  rel=p.relative_to(R/'firmware').as_posix();txt=read(p)
  lines=colored_lines(txt)
  inner=f'<main class="code-page"><a href="../{NAME}.html">← 返回技术文档</a><h2>{html.escape(rel)}</h2><p><a href="../firmware/{rel}">下载源文件</a></p><div class="code-lines">{lines}</div></main>'
  (R/'code'/code_name(rel)).write_text(shell(rel,top('../')+inner,prefix='../'),encoding='utf-8')
 home=(R/'tools/home.template.html').read_text(encoding='utf-8').replace('{DOC}',NAME)
 (R/'index.html').write_text(shell('电子琴设计',top()+home+footer()),encoding='utf-8')
 print('HTML, home and source viewers built; headings',len(headings))
if __name__=='__main__':main()
