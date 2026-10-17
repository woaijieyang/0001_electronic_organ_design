from pathlib import Path
import html
R=Path(__file__).resolve().parents[1];D=R/'assets/diagrams';F=R/'assets/figures'
D.mkdir(exist_ok=True,parents=True);F.mkdir(exist_ok=True,parents=True)
graphs={
'system':'''flowchart TB
 subgraph input[演奏者的输入]
  K[七个琴键] ~~~ E[编码器与功能键] ~~~ J[摇杆]
 end
 subgraph app[STM32 应用逻辑]
  N[音高与音色] ~~~ S[模式与参数] ~~~ A[和弦与伴奏序列]
 end
 subgraph output[可以听见和看见的反馈]
  P[旋律 · TIM2 / PA0] ~~~ Q[伴奏 · TIM3 / PA7] ~~~ V[OLED 与节拍灯]
 end
 K --> N
 E --> S
 J --> A
 N --> P
 A --> Q
 S --> V
''',
'clock':'''flowchart LR
 H[HSE 8 MHz] --> P[PLL × 9]
 P --> C[SYSCLK / HCLK\n72 MHz]
 C --> A[APB1 ÷ 2\n36 MHz]
 A --> T[TIM2 / TIM3\n定时器时钟 × 2]
 T --> B[PSC + 1 分频]
 B --> N[ARR + 1 = 100\n输出 PWM]
''',
'note':'''flowchart TB
 A[PB12 按下 · 上升沿] --> B[EXTI15_10_IRQHandler\n检查 EXTI12 与输入电平]
 B --> C[普通音色分支\nBuzzer_Reset 通道 1]
 C --> D[频率 = 262 × 1 × 2 × 1\n默认值 524 Hz]
 D --> E[Buzzer_ON\nTIM2：PSC = 1373 / CCR = 50]
 E --> F[定时器持续输出]
 F --> G[PB12 松开 · 下降沿\nCCR = 0，关闭旋律通道]
''',
'chord':'''flowchart LR
 A[音序 number] --> B{等于 0？}
 B -->|是| Z[返回 0]
 B -->|否| C[序号减 1]
 C --> D[模 4 选和弦音\n除 4 选八度]
 H[chordType\n选择结构与根音倍率] --> D
 D --> E[转换为整数 freq]
 E --> F[乘 transpose 的 tsp 项\n返回和弦频率]
''',
'accompaniment':'''flowchart TB
 A[acmp 选择风格数组] --> B[introPlay\nisPlaying = 1]
 B --> C{前奏开启？}
 C -->|是| D[播放 beat 个前奏鼓事件]
 C -->|否| E[进入主段]
 D --> E
 E --> F[按当前 i 读取摇杆\n更新和弦]
 F --> G{摇杆按下？}
 G -->|是| H[从 i % beat 开始加花\n到组末后回主段首项]
 H --> E
 G -->|否| I[点亮 LED\n按 track 输出鼓与琶音]
 I --> J[读取编码器调速度\n检查结束按键]
 J -->|继续| K[i 前进，序列结束后回 0]
 K --> F
 J -->|结束| L[endingPlay\n按 section 播放尾声]
 L --> M[收尾等待 500 ms\nisPlaying = 0]
''',
'modes':'''stateDiagram-v2
 [*] --> 音色设置
 音色设置 --> 伴奏设置: 摇杆按压 / knob 回 1
 伴奏设置 --> 音色设置: 摇杆按压 / knob 回 1
 伴奏设置 --> 播放中: 左功能键 / acmp
 播放中 --> 伴奏设置: 编码器按键 / 尾声与收尾
 音色设置: Voice · Transp · Shift
 伴奏设置: Style · Tempo · ArpVoc
 播放中: 和弦 · 加花 · 速度 · 旋律演奏
''',
'layers':'''flowchart TB
 M[User/main.c\n状态 · 音乐 · 模式 · 琴键 ISR]
 M --> B[Buzzer\n频率 / 占空比 / 时长]
 M --> I[Key / Keyboard / Encoder\n按键与方向事件]
 M --> J[JoyStick / AD\n模拟位置与按压]
 M --> O[OLED / LED\n可见反馈]
 B --> P[System/PWM.c\nTIM2 / TIM3]
 B --> D[System/Delay.c\nSysTick 轮询]
 P --> L[ST 标准外设库 / CMSIS]
 I --> L
 J --> L
 O --> L
 D --> L
''',
'interrupts':'''sequenceDiagram
 participant U as 主程序 / 伴奏
 participant X as EXTI 中断
 participant T as 定时器 PWM
 U->>T: 配置伴奏通道频率与占空比
 Note over T: 硬件持续计数并输出
 U->>U: 等待或处理下一事件
 Note over X: 琴键边沿到来
 X->>X: 检查标志与输入电平
 X->>T: 更新旋律通道
 X->>X: 清除中断标志
 X-->>U: 返回被中断的位置
 U->>U: 继续原流程
''',
'debug':'''flowchart TB
 A[梳理整体流程与复现条件] --> B[排除基础配置问题]
 B --> C[分层隔离测试]
 C --> D[检查模块内部逻辑与模块间接口]
 D --> E[恢复连续运行并回归整体验证]
''',
'validation':'''flowchart LR
 A[上电与屏幕\n默认参数] --> B[单键与松键\n两路声音]
 B --> C[音色与音域\n范围与边界]
 C --> D[六种伴奏\n速度与音轨]
 D --> E[和弦与加花\n前奏和尾声]
 E --> F[返回设置\n再做一轮操作]
''',
'project':'''flowchart LR
 P[Project.uvprojx] --> U[User\nmain 与中断模板]
 P --> H[Hardware\n部件接口与显示字库]
 P --> S[System\nPWM 与 Delay]
 P --> L[Library\nST 标准外设库]
 P --> B[Start\n启动向量与时钟]
''',
}
for name,src in graphs.items():(D/(name+'.mmd')).write_text(src,encoding='utf-8')

def svg(w,h,content):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><style>text{{font-family:Microsoft YaHei,Noto Sans CJK SC,sans-serif;fill:#28282d}}.title{{font-size:24px;font-weight:700}}.small{{font-size:16px;fill:#66636a}}.label{{font-size:19px;font-weight:600}}</style><rect width="100%" height="100%" fill="#fffdf9"/>'+content+'</svg>'
def txt(x,y,s,cls='',fill=''):
 return f'<text x="{x}" y="{y}" class="{cls}"'+(f' style="fill:{fill}"' if fill else '')+'>'+html.escape(s)+'</text>'

c=txt(36,45,'引脚与外设资源','title')+txt(36,74,'每条连接都能回到一个明确的初始化入口','small')
groups=[('音乐输出','TIM2_CH1  →  PA0','TIM3_CH2  →  PA7'),('七个琴键','PB12 / PB13 / PA8 / PA11','PB3 / PB6 / PB9 · 双边沿 EXTI'),('功能与编码器','PA10 / PB15 / PB14 / PA9','PB0 / PB1 · 下降沿 EXTI'),('摇杆输入','PA5 → ADC5 · PA3 → ADC3','PA1 → 低有效按压'),('OLED 显示','PC15 → SCL · PC14 → SDA','开漏 GPIO · 模拟 I²C'),('节拍灯','PA6 / PA4 / PA2','推挽 GPIO · 低电平点亮')]
for i,(title,a,b) in enumerate(groups):
 x=36+(i%2)*446;y=102+(i//2)*142
 c+=f'<rect x="{x}" y="{y}" width="422" height="120" rx="12" fill="#fff" stroke="#e6d8d4"/><rect x="{x}" y="{y}" width="5" height="120" rx="2" fill="#8f1d2c"/>'
 c+=txt(x+20,y+32,title,'label')+txt(x+20,y+66,a,'small')+txt(x+20,y+94,b,'small')
(F/'resources.svg').write_text(svg(940,550,c),encoding='utf-8')
c=txt(34,43,'摇杆采样值 → 和弦选择','title')+txt(34,72,'先判断四角，再判断单轴；中心保持前一次和弦','small')
xs=['vrX < 1024','1024 ≤ vrX ≤ 3072','vrX > 3072'];ys=['vrY > 3072','1024 ≤ vrY ≤ 3072','vrY < 1024'];names=[['Am','G7','G'],['C','保持','F'],['Dm','Em','E7']]
for j,s in enumerate(xs):c+=txt(220+j*240,110,s,'small')
for i in range(3):
 y=130+i*115;c+=txt(25,y+60,ys[i],'small')
 for j in range(3):
  x=210+j*240;center=i==j==1
  c+=f'<rect x="{x}" y="{y}" width="220" height="96" rx="12" fill="'+('#f2eee7' if center else '#f9e9e8')+'" stroke="#e1ccc9"/>'
  c+=txt(x+82,y+59,names[i][j],'title','#8f1d2c')
(F/'joystick.svg').write_text(svg(950,500,c),encoding='utf-8')
c=txt(34,43,'OLED 字符界面','title')+txt(34,73,'128 × 64 像素 · 8 × 16 字模 · 4 行 × 16 列','small')
screens=[('音色模式',['1 Clarinet','Tsp:  0  Sft:  0','K: Voice  M: Voc','OctDw OctUp Shrp']),('伴奏待机',['1 8Beat','Tempo: 120 ArpV1','K: Style  M: Sty','Play Dr&Ap In&Ed'])]
for i,(title,lines) in enumerate(screens):
 x=34+i*450;c+=txt(x,120,title,'label');c+=f'<rect x="{x}" y="140" width="424" height="220" rx="14" fill="#19222b"/>'
 for j,line in enumerate(lines):
  c+=f'<text x="{x+22}" y="{182+j*46}" style="font:25px Consolas,monospace;fill:#d4f5f3">{html.escape(line)}</text>'
c+=txt(34,405,'模式与旋钮任务始终可见；固定字段与空格清除保持页面稳定。','small')
(F/'display.svg').write_text(svg(940,440,c),encoding='utf-8')
# Curated native layout of the same system/mode relationships, for legible reading.
arrow='<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 Z" fill="#8f1d2c"/></marker></defs>'
def edge(x1,y1,x2,y2):return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#8f1d2c" stroke-width="2" marker-end="url(#arrow)"/>'
def box(x,y,w,h,title,subtitle):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#fff" stroke="#d8c3bc"/>'+txt(x+18,y+34,title,'label')+txt(x+18,y+65,subtitle,'small')
c=arrow+txt(34,43,'从输入，到音乐逻辑，再到声音与反馈','title')+txt(34,76,'三条主要信号路径 · 状态参数在应用层共享','small')
for x,label in [(34,'INPUT / 操作'),(364,'LOGIC / 应用'),(694,'OUTPUT / 输出')]:c+=txt(x,124,label,'small')
rows=[('七个琴键','按下与松开边沿','音高与音色','查表 · 倍率 · 占空比','旋律声音','TIM2_CH1 / PA0'),('旋钮与功能键','参数选择和临时控制','模式与参数','mode · knob · isPlaying','可见反馈','OLED / 节拍 LED'),('摇杆','位置采样与按压','和弦与伴奏','chordType · 事件序列','伴奏声音','TIM3_CH2 / PA7')]
for i,row in enumerate(rows):
 y=148+i*130
 for j in range(3):c+=box(34+330*j,y,280,94,row[2*j],row[2*j+1])
 c+=edge(319,y+47,357,y+47)+edge(649,y+47,687,y+47)
c+=txt(34,572,'旋律与伴奏使用独立硬件通道；鼓点与琶音在伴奏通道内顺序播放。','small')
(F/'system.svg').write_text(svg(1010,610,c),encoding='utf-8')
c=arrow+txt(34,43,'有限的按键，清楚的操作语境','title')+txt(34,76,'mode 区分设置模式，isPlaying 区分待机与演奏','small')
c+=box(75,145,340,110,'音色设置 · mode = 1','Voice / Transp / Shift')
c+=box(555,145,340,110,'伴奏设置 · mode = 2','Style / Tempo / ArpVoc')
c+=box(315,375,340,110,'伴奏播放 · isPlaying = 1','和弦 / 加花 / 速度 / 琴键演奏')
c+=edge(420,170,549,170)+txt(437,151,'摇杆按压','small')
c+=edge(550,233,422,233)+txt(437,218,'摇杆按压','small')
c+=f'<path d="M760,262 L760,430 L662,430" fill="none" stroke="#8f1d2c" stroke-width="2" marker-end="url(#arrow)"/>'
c+=txt(775,326,'左功能键','small')+txt(775,351,'启动伴奏','small')
c+=f'<path d="M485,370 L485,290 L615,290 L615,262" fill="none" stroke="#8f1d2c" stroke-width="2" marker-end="url(#arrow)"/>'
c+=txt(332,328,'编码器按键','small')+txt(332,353,'尾声与收尾','small')
c+=txt(75,548,'切换设置模式时 knob 回到 1；伴奏结束后 isPlaying 回到 0。','small')
(F/'modes.svg').write_text(svg(970,580,c),encoding='utf-8')
c=arrow+txt(34,43,'电子琴的五步调试流程','title')
steps=[
 ('梳理整体流程','固定模式、参数与操作顺序','沿输入、状态、计算和输出确定观察位置'),
 ('排除基础配置问题','检查工程路径、接线、时钟、GPIO 与中断','从电平变化开始，再看中断映射和使能'),
 ('分层隔离测试','直接传入有效频率与占空比，单独测试声音输出','根据结果转向驱动和硬件，或回查输入与计算'),
 ('检查内部逻辑与模块接口','核对倍率、事件索引、共享变量和调用顺序','一次只改变相关条件，恢复连续运行检查时序'),
 ('回归整体验证','重复原异常操作，再检查模式切换和完整演奏','记录现象、假设、验证结果与修改原因'),
]
for i,(title,a,b) in enumerate(steps):
 y=78+i*135
 c+=f'<circle cx="56" cy="{y+51}" r="22" fill="#8f1d2c"/>'+txt(50,y+58,str(i+1),'label','#fff')
 c+=f'<rect x="99" y="{y}" width="778" height="108" rx="12" fill="#fff" stroke="#d8c3bc"/>'
 c+=txt(122,y+31,title,'label')+txt(122,y+62,a,'small')+txt(122,y+87,b,'small')
 if i<4:c+=edge(488,y+111,488,y+129)
(F/'debug.svg').write_text(svg(920,772,c),encoding='utf-8')
print('diagram sources',len(graphs),'native svg',6)
