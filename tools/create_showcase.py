"""Native SVG assets for the project showcase and GitHub README."""
from pathlib import Path
import base64,html
R=Path(__file__).resolve().parents[1];F=R/'assets/figures'
RED='#8f1d2c';INK='#28232a';MUTED='#71666b';BG='#fffaf3'
def data(name):
 p=R/name;mime='image/png' if p.suffix=='.png' else 'image/jpeg'
 return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode()
def text(x,y,s,size=22,color=INK,weight='400',family='Microsoft YaHei'):
 return f'<text x="{x}" y="{y}" fill="{color}" font-family="{family},sans-serif" font-size="{size}" font-weight="{weight}">{html.escape(s)}</text>'
def rect(x,y,w,h,fill,rad=0,stroke='none'):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rad}" fill="{fill}" stroke="{stroke}"/>'
def write(n,w,h,c):
 (F/(n+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'+c+'</svg>',encoding='utf-8')

# A readable cover at GitHub's usual 830px article width.
c=rect(0,0,1440,650,BG)+rect(0,0,13,650,RED)
c+=f'<image x="62" y="48" width="54" height="54" xlink:href="{data("assets/photos/sdu-emblem.png")}"/>'
c+=text(132,74,'山东大学',25,RED,'600')+text(132,99,'SHANDONG UNIVERSITY',12,MUTED)
c+=text(63,163,'STM32  /  PROJECT 2024',15,RED,'600')
c+=text(56,253,'电子琴设计',73,INK,'700','SimSun')
c+=text(64,305,'从第一次发声，到完整演奏。',28,RED)
c+=text(64,355,'七个琴键 · 双路 PWM · 六种伴奏',21,MUTED)
c+=rect(64,389,61,3,RED)+text(64,438,'张鑫  /  程序开发',19,INK)
c+=rect(670,107,700,408,'#efe3d8',18)
c+=f'<image x="686" y="123" width="668" height="376" preserveAspectRatio="xMidYMid meet" xlink:href="{data("assets/photos/instrument.jpg")}"/>'

# Seven small native keys as the visual signature, not a photo manipulation.
for i in range(7):
 c+=rect(64+i*66,490,57,90,RED if i==2 else '#f0e6dc',5)
 c+=text(82+i*66,559,str(i+1),20,'#fff' if i==2 else MUTED)
c+=text(64,617,'音高计算  /  节奏编排  /  交互控制',15,MUTED)
write('readme-cover',1440,650,c)

c=rect(0,0,1160,660,BG)+text(44,54,'演奏，发生在这些操作之间',30,INK,'600')
c+=text(44,87,'七键演奏 · 旋钮调参 · 摇杆和弦',18,MUTED)
c+=rect(44,119,652,470,'#f0e5db',18)+rect(722,119,394,470,'#f7eee5',18)
c+=text(68,155,'琴键与功能键',21,RED,'600')
c+=rect(76,180,588,115,'#25252c',10)
for j,s in enumerate(['1 Clarinet','Tsp:  0  Sft:  0','K: Voice  M: Voc']):c+=text(99,211+j*29,s,21,'#dce8df','400','Consolas')
for i,s in enumerate(['降八度','升八度','升半音']):
 c+=rect(76+i*202,315,184,48,'#fffaf3',8)+text(104+i*202,346,s,19,INK)
for i,n in enumerate([524,588,660,698,784,880,988]):
 x=76+i*85;c+=rect(x,391,74,162,'#fffdf9',7,'#d2bdb1')
 c+=rect(x+10,403,54,5,RED if i in [0,3,6] else '#bda99b',2)
 c+=text(x+27,474,str(i+1),29,RED,'600')+text(x+15,523,str(n),16,MUTED)
c+=text(747,156,'旋钮',21,RED,'600')
c+='<circle cx="790" cy="206" r="27" fill="#8f1d2c"/><path d="M790 182 V195" stroke="#fff" stroke-width="3"/>'
c+=text(838,198,'按下选择参数',18,INK)+text(838,230,'旋转修改数值',18,MUTED)
c+=text(749,284,'音色 / 移调 / 平移',18,INK)+text(749,313,'风格 / 速度 / 琶音音色',18,MUTED)
c+=rect(747,339,344,1,'#d7c5b8')+text(747,379,'摇杆',21,RED,'600')
c+='<circle cx="790" cy="431" r="28" fill="#25252c"/><path d="M790 405 V457 M764 431 H816" stroke="#fffaf3" stroke-width="2"/>'
c+=text(838,422,'偏转选择和弦',18,INK)+text(838,454,'播放时按下加花',18,MUTED)
c+=text(749,513,'C · Dm · Em · E7',19,INK)+text(749,547,'F · G · G7 · Am',19,MUTED)
c+=text(44,631,'默认七键频率 / Hz',17,MUTED)
write('controls',1160,660,c)

c=rect(0,0,1320,292,BG)+text(42,51,'从接线，到能够完整演奏',28,INK,'600')
stages=[('接通硬件','安排引脚与输入输出'),('琴键发声','把音高换算成 PWM'),('组织伴奏','用数组写音符和节奏'),('加入交互','旋钮、摇杆与屏幕'),('整机联调','连接声音与操作')]
c+='<path d="M90 132 H1200" stroke="#d5bdb2" stroke-width="2"/>'
for i,(a,b) in enumerate(stages):
 x=50+i*253;c+=f'<circle cx="{x+24}" cy="132" r="23" fill="{RED if i%2==0 else "#59414a"}"/>'
 c+=text(x+17,140,str(i+1),21,'#fff','600')+text(x,205,a,24,RED,'600')+text(x,244,b,18,MUTED)

write('design-journey',1320,292,c)

c=rect(0,0,1080,60,BG)
chips=[('STM32F103C8',207),('C / Keil',143),('双路 PWM',167),('EXTI / ADC',171),('OLED / I²C',178)]
x=22
for t,w in chips:
 c+=rect(x,9,w,42,'#f1e3dc',21)+text(x+18,37,t,17,RED,'600');x+=w+14
write('tech-stack',1080,60,c)
print('4 showcase SVG assets written')
