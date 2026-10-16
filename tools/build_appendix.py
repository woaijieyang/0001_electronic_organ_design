"""Rebuild the documented application/driver index from the preserved firmware."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
def read(p):
    b=p.read_bytes()
    for e in ('utf-8-sig','gb18030'):
        try:return b.decode(e).replace('\r\n','\n').replace('\r','\n')
        except UnicodeDecodeError:pass
    raise ValueError(p)
def link(file,line,label='源码'):
    return f'[{label}](firmware/{file}#L{line})'
def cell(s):return str(s).replace('|','&#124;').replace('\n',' ')
def table(head,rows):
    return '\n| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+''.join('| '+' | '.join(cell(c) for c in r)+' |\n' for r in rows)+'\n'

GLOBALS={
'voice':('uint8_t；1—6，初值1','主程序由编码器更新；琴键中断读取；切入伴奏时将鼓组6复位为1','1—5索引五项占空比，6进入鼓组分支；1作为首个菜单项。改变它改变下一次按键的声音生成方式。'),
'knob':('uint8_t；1—3，初值1','主循环按PA9递增；切换mode后重置1；参数分支读取','同一个旋钮选择三种任务，节省输入器件；值越界会脱离已有菜单分支。'),
'tsp':('uint8_t；0—11，初值5','主循环限幅更新；琴键频率与chord读取；OLED显示tsp-5','5对应倍率1；增加一项约升半音，减小约降半音；旋律和和弦共享移调。'),
'sft':('uint8_t；0—6，初值3','主循环限幅更新；七键频率计算读取；OLED显示sft-3','3使首键选scale[3]=262；最大6保证第七键索引12；改变自然音窗口而非统一半音移调。'),
'oct':('uint8_t；0/1/2，初值1','PA10/PB15边沿修改，松开恢复1；七键频率读取','对应1/2/4倍率；1是界面默认，按下降八度为0、升八度为2；下一次琴键发声时生效。'),
'sharp':('uint8_t；0/1，初值0','PB14边沿修改；旋律计算和第六/七鼓键读取','0时倍率1，1时乘1.06；鼓组下在6/8及7/9鼓编码间选择。'),
'mode':('uint8_t；1/2，初值1','摇杆按压在主循环切换；主循环及功能键中断读取','1音色设置，2伴奏设置；把相同硬件映射到两组任务，切换时清屏并重置knob。'),
'style':('uint8_t；1—6，初值1','主循环循环更新；显示和acmp(style)读取','1默认8Beat；不同编号选择不同局部序列和beat；编号必须与styleNames及六分支一致。'),
'tempo':('uint16_t；40—240 BPM，初值120','主循环及前奏、加花、主段读取编码器后更新；时长公式读取','120对应四分音符500ms；步长5兼顾调节跨度与操作次数；增大使标称子步缩短。'),
'chordType':('uint8_t；0—7，初值0','主段和尾声在启用琶音时由摇杆修改；chord和显示读取','0默认C；按八方向选择结构与根音；中心不写入，保持此前和弦。'),
'isPlaying':('uint8_t；0/1，初值0','introPlay置1，endingPlay末尾置0；功能键中断读取','即使关闭前奏仍在进入播放时置1；1使三功能键用于临时音高控制。'),
'track':('uint8_t；0—2，初值0','伴奏待机的PB15更新；各播放函数读取','0第一鼓轨+琶音，1两条鼓轨，2仅琶音；控制调用或等待的分支，不增加硬件通道。'),
'section':('uint8_t；0—3，初值0','伴奏待机的PB14更新；introPlay/endingPlay读取','0前奏+尾声，1仅前奏，2仅尾声，3均关闭；主段播放仍存在。'),
'arpVoice':('uint8_t；1—5，初值1','伴奏待机旋钮循环更新；主段和尾声读取','只索引5项旋律占空比，独立于voice；增加编号使脉冲占空比从50%逐步减至10%。'),
'Encoder_Count':('int8_t；−1/0/+1，静态零初始化','EXTI0/1赋+1/−1；Encoder_Get读取；Encoder_Clear清零','表示最近的方向事件。符号供step相乘，0表示当前无待处理方向；主程序处理后清零。'),
}
ARRAYS={
'scale':'uint16_t[13]，单位Hz；七键读取索引k+sft，13项覆盖7键与0—6平移窗口；数值增大使相应基础音更高。',
'transpose':'float[12]；对应−5至+6半音的近似倍率；琴键和和弦计算读取，索引5为1.0；更改数值会同时改变相关移调和以该表构造的和弦根音。',
'voiceDuties':'uint8_t[5]，单位%；voice/arpVoice减1索引；每项是CCR值，ARR+1=100；降低数值缩短高电平脉冲并改变谐波。',
'voiceNames':'char*[6]；voice−1索引的界面名称；字符串长度决定清除旧文字区域的需要；顺序应与声音分支一致。',
'styleNames':'char*[6]；style−1索引的伴奏名称；改变文字只影响显示，改变编号顺序需要对应acmp分支。',
'trackStatus':'char*[3]；track索引；Dr&Ap、Drums、Arpgo分别概括鼓+琶音、双鼓、琶音；短标签适配5字符区域。',
'sectionStatus':'char*[4]；section索引；In&Ed、Intro、Endng、OFF；填充空格覆盖旧文字，状态值决定前尾奏组合。',
'chordNames':'char*[8]；chordType索引；两字符宽，C/F/G补空格；文字与八个和弦分支对应。',
'major':'uint16_t[4]，Hz；大三和弦根音、三音、五音、上八度根音；%4索引，/4控制更高八度；更改第三度或第七度会改变和弦结构。',
'minor':'uint16_t[4]，Hz；三音用156替代165，形成小三和弦结构；用于Dm、Em、Am；根音移动在此数组之外计算。',
'seventh':'uint16_t[4]，Hz；第四项233为降七度而非262上八度根音；用于E7/G7；数组音程决定属七色彩。',
}
PURPOSE={
'AD_Init':'使能GPIOA和ADC1，选择12MHz ADC时钟，单通道软件触发，并在启用后复位校准、启动校准。',
'AD_GetValue':'选择一个规则通道，55.5周期采样，软件触发后等待EOC，返回12位转换值。',
'Buzzer_Init':'初始化TIM2/CH1与TIM3/CH2两路PWM。',
'Buzzer_OFF':'按通道将比较值设为0，PWM波形转为静音状态。',
'Buzzer_ON':'目标频率非零时设置频率和占空比；零频率通过静音处理，避免进入频率除法。',
'Buzzer_Timing':'开启声音，阻塞等待timing毫秒，然后关闭指定通道。',
'Buzzer_Reset':'换音前设置临时预分频并把CNT写为51，为随后发声准备计数位置。',
'Buzzer_Drum':'将0—9鼓声编号解释为定频、交替频率或下降扫描动作。',
'Encoder_Init':'配置PB0/1上拉、下降沿EXTI和NVIC，建立方向事件入口。',
'Encoder_Get':'返回当前方向事件−1/0/+1，不清零。',
'Encoder_Clear':'把方向事件清零，表示主程序已消费。',
'Encoder_Var':'执行var+=方向×step，按上下界映射setL/setH，清除事件后返回新值。',
'EXTI0_IRQHandler':'PB0下降沿且PB1为低时写入+1，再清除EXTI0标志。',
'EXTI1_IRQHandler':'PB1下降沿且PB0为低时写入−1，再清除EXTI1标志。',
'JoyStick_Init':'PA1上拉读取按压；初始化PA3/PA5模拟采样。',
'JoyStick_GetSW':'将低有效输入转换为按下1、松开0。',
'JoyStick_GetX':'读取ADC通道5；返回横轴命名对应的采样值。',
'JoyStick_GetY':'读取ADC通道3；返回纵轴命名对应的采样值。',
'Key_Var_Plus':'增加step；按步长符号检查边界max，越界后写set，实现循环选择。',
'Keyboard_Init':'为七琴键和三个功能键建立双边沿EXTI；释放JTAG占用的PB3。',
'OLED_I2C_Init':'PC14/15开漏输出，先释放SDA/SCL为高。',
'OLED_I2C_Start':'在SCL高时让SDA从高变低，随后拉低SCL。',
'OLED_I2C_Stop':'在SCL高时让SDA从低变高。',
'OLED_I2C_SendByte':'按最高位到最低位发送8位，再提供一个额外时钟。',
'OLED_WriteCommand':'发送0x78地址、0x00控制字及一个命令字节。',
'OLED_WriteData':'发送0x78地址、0x40控制字及一个图像数据字节。',
'OLED_SetCursor':'以页号Y和列号X设置显示存储器写入位置。',
'OLED_Clear':'遍历8页×128列写0，清空1024字节显示区域。',
'OLED_ShowChar':'从8×16字模取上下两半，各写8字节。',
'OLED_ShowString':'从String[0]写到字符串终止符，列坐标逐字符递增。',
'OLED_Pow':'从Result=1开始连乘X，重复Y次，返回整数幂。',
'OLED_ShowNum':'用十进制幂逐位取数，固定Length位，高位不足补0。',
'OLED_ShowSignedNum':'先写符号，再对绝对值逐位取数；0的符号位置写空格。',
'OLED_ShowHexNum':'按16进制逐位取数；0—9转数字，10—15转A—F。',
'OLED_ShowBinNum':'按2进制逐位取数，输出固定Length位的0/1。',
'OLED_Init':'上电忙等，初始化总线，发送屏幕配置序列，开启显示并清屏。',
'Delay_us':'使用24位SysTick、72MHz时钟和COUNTFLAG轮询执行微秒延时。',
'Delay_ms':'每次循环调用Delay_us(1000)，按毫秒累加等待。',
'Delay_s':'每次循环调用Delay_ms(1000)，按秒累加等待。',
'chord':'由number、chordType和tsp计算和弦音频率，number为0直接返回0。',
'introPlay':'置isPlaying=1，根据section播放一组前奏鼓点，更新灯光并检查速度。',
'endingPlay':'根据section和track播放尾声，等待后置isPlaying=0并清理显示。',
'acmpPlay':'循环处理和弦读取、加花、LED、鼓/琶音输出、速度与结束操作。',
'acmp':'按style建立五类局部数组及number/beat参数，再进入公共播放函数。',
'main':'依次初始化各模块，循环处理两种模式的显示、参数和启动操作。',
'EXTI3_IRQHandler':'处理PB3第五琴键的按下与松开。',
'EXTI9_5_IRQHandler':'按EXTI8、6、9顺序处理第三、第六、第七琴键。',
'EXTI15_10_IRQHandler':'按EXTI11、12、13、10、15、14顺序处理第四、第一、第二琴键与三功能键。',
}
PARAM={
'pins':'引脚位掩码，可用按位或组合；对应端口由函数名/实现固定。初始化函数写配置，读函数查询输入，LED函数写输出；改变掩码会改变实际参与操作的引脚。',
'ADC_Channel':'本项目调用值为ADC_Channel_5或ADC_Channel_3；在规则序列第1位配置，决定读取哪条模拟输入，返回值单位为ADC计数。',
'channel':'取0/1/2：同时操作两路/旋律TIM2/伴奏TIM3；由调用者选择并在函数分支读取，改变它会把声音或静音动作送到不同输出。',
'freq':'单位Hz，uint16_t输入；Buzzer_ON以0表示静音，正数送到PWM预分频计算；更高值使计数周期缩短。PWM_SetFreq自身要求非零。',
'tone':'单位%，本项目旋律为50/40/30/20/10，鼓声使用50/30/10；送入CCR，在固定ARR=99下直接决定高电平计数数目。',
'timing':'单位ms，uint16_t；由伴奏单步剩余时长或30/60传入，延时函数读取；增大会延长发声并推迟后续事件。',
'type':'鼓声编号0—9；0等待30ms，其他编号选择具体频率序列；无外部持久状态，在switch中读取。',
'var':'int16_t当前值的局部副本；函数按step更新并返回，调用者赋回状态量才持久生效；采用有符号数便于处理负步长。',
'step':'int8_t步长；参数选择为1，速度为5；编码器方向与其相乘，改变符号反转调节方向，改变绝对值改变一次操作幅度。',
'min':'int16_t下限；更新后的var小于它时映射到setL；与数组可用索引或业务范围一致。',
'max':'int16_t边界；Encoder_Var中为上限；Key_Var_Plus中正步长检查上限、负步长检查下限；越界后采用指定返回位置。',
'setL':'低于min后的返回值；等于min为下限保持，等于max为循环到末项；只在低端越界时读取。',
'setH':'高于max后的返回值；等于max为上限保持，等于min为循环到首项；只在高端越界时读取。',
'set':'Key_Var_Plus越界后的值；knob/mode回到1，track/section回到0；决定循环起点。',
'Byte':'uint8_t待发送字节；发送循环用0x80右移逐位取出，从最高位开始；取值0—255，每一位决定当前SDA电平。',
'Command':'uint8_t控制器命令或参数；写命令函数将其发到控制通道；具体字节含义见OLED命令表。',
'Data':'uint8_t图像字节；一字节控制当前页同一列的8个纵向像素；0全灭、0xFF全亮，按数据通道发送。',
'Line':'uint8_t字符行，1—4；换算页号为(Line−1)×2；增加1向下移动16像素。',
'Column':'uint8_t字符列，1—16；换算X为(Column−1)×8；增加1向右移动8像素，字符串和数字还占据后续列。',
'Char':'char可见ASCII；减去空格编码32作为字模索引；选择一个8×16图样，字符数据需落在字模提供的范围内。',
'String':'char*以零结尾字符串；只读取不修改，i递增到终止符停止；长度决定占用字符列，显示调用负责选择能容纳的区域。',
'Number':'显示的整数；有符号函数先分离符号和绝对值，其他函数按进制逐位取数；改变它只改变显示内容，不修改原状态。',
'Length':'uint8_t输出位数；十进制1—10、十六进制1—8、二进制驱动约定1—16；不足补0，过小只保留相应低位；符号函数额外占1列。',
'duty':'uint16_t比较值；本工程ARR+1=100，可用0—100表达0%—100%；0用于静音；设置后改变高电平持续比例。',
'xus':'uint32_t微秒数；LOAD按72×xus设置，24位计数器可容纳到233016μs，原注释保守写233015；项目实际使用1000；增大延长等待。',
'xms':'uint32_t毫秒数；while(xms--)逐次消耗本地副本，每次等待1000μs；增大时CPU停留在阻塞等待更久。',
'xs':'uint32_t秒数；while(xs--)逐次等待1000ms；此接口保留作通用服务，主应用未直接调用。',
'introDrums':'char数组指针；索引j=0…beat−1，每项为0—9鼓声编号；修改排列改变前奏第一鼓轨；调用时实际传fillDrums。',
'introCymbals':'char数组指针；长度至少beat，与introDrums逐项配对；修改内容改变前奏第二鼓轨，调用时传fillCymbals。',
'arp':'char数组指针；至少number项，0休止、1—8和弦音序；非零送chord计算；零进入独立等待分支。',
'drums':'char数组指针；至少number项，0—9鼓声编号；每步第一鼓轨，track=2时以等待替代。',
'cymbals':'char数组指针；至少number项，0—9鼓声编号；track=1时作为第二鼓轨，其他组合使用琶音。',
'fillDrums':'char数组指针；至少beat项；同时用于前奏和加花第一鼓轨，加花从当前子步开始读。',
'fillCymbals':'char数组指针；至少beat项；与fillDrums配对，为前奏和加花第二鼓轨。',
'beat':'char，调用值6/8/12/16；决定每组子步数、延时公式、灯光分组与加花边界；值来自当前风格定义。',
'style':'char局部形参，调用值1—6，来自全局style；决定选择哪组序列；形参与同名全局变量分别占据不同作用域。',
}
CFG={
'GPIO_Mode':{'GPIO_Mode_IPD':'输入下拉：悬空/松开时趋向低，按键接正电源后读高。','GPIO_Mode_IPU':'输入上拉：松开时为高，触点闭合到低电平；驱动按低有效解释。','GPIO_Mode_AIN':'模拟输入，供ADC采样连续电压；改为数字输出会改变采样对象的电气行为。','GPIO_Mode_AF_PP':'复用推挽输出，交给定时器驱动PWM；普通GPIO输出不会自动跟随定时器。','GPIO_Mode_Out_PP':'普通推挽输出，供LED使用；置低点亮，置高熄灭。','GPIO_Mode_Out_OD':'开漏输出：拉低或释放，适配I²C总线；高电平由上拉形成。'},
'GPIO_Speed':'50MHz输出驱动速度等级；音乐频率由定时器设置，ADC时钟由PCLK2分频得到。',
'GPIO_Pin':'位掩码选择当前端口参与初始化的引脚；多个GPIO_Pin用或运算组合，各具体连接见硬件表；改动必须同步接线与EXTI/ADC映射。',
'ADC_Mode':'Independent表示独立ADC，不使用双ADC联合模式；与只读取ADC1的接口一致。',
'ADC_DataAlign':'Right表示12位结果右对齐，可直接按0—4095比较；改为左对齐需同步阈值和读取解释。',
'ADC_ExternalTrigConv':'None表示不以外部事件启动，由软件触发；变更后采样启动条件随之改变。',
'ADC_ContinuousConvMode':'DISABLE：一次触发转换一次，便于先换通道再取值；连续模式会改变结果更新节奏。',
'ADC_ScanConvMode':'DISABLE：不自动扫描多通道，X/Y由调用顺序分别选择。',
'ADC_NbrOfChannel':'1表示规则序列只有一个位置；与RegularChannelConfig中的rank=1一致。',
'EXTI_Line':'选择外部中断线，必须与GPIO_EXTILineConfig端口映射对应；同编号端口引脚共享一条EXTI线。',
'EXTI_LineCmd':'ENABLE使相应线参与中断；禁用后输入电平仍可读取，但不会从该线进入ISR。',
'EXTI_Mode':'Interrupt选择中断请求，由NVIC调度；不同于仅生成硬件事件。',
'EXTI_Trigger':{'EXTI_Trigger_Falling':'下降沿用于编码器触点动作，配合另一相电平决定方向。','EXTI_Trigger_Rising_Falling':'双边沿同时观察琴键按下和松开，使发声/静音或临时音高状态成对更新。'},
'NVIC_IRQChannel':'选择向量入口；EXTI0/1独立，EXTI9_5和EXTI15_10共享多条线，ISR内进一步检查标志。',
'NVIC_IRQChannelCmd':'ENABLE允许该中断通道进入服务；与EXTI线使能共同生效。',
'NVIC_IRQChannelPreemptionPriority':'抢占优先级，PriorityGroup_2下0—3；编码器1、琴键2，数值越小优先；变化会改变中断相互抢占关系。',
'NVIC_IRQChannelSubPriority':'子优先级，PriorityGroup_2下0—3；同抢占级同时待处理时按此排序，数值越小先服务；不产生同级抢占。',
'TIM_ClockDivision':'TIM_CKD_DIV1选择数字滤波/死区采样时钟的1倍分频；PWM计数频率由PSC控制。',
'TIM_CounterMode':'Up从0向ARR计数；与PWM1比较关系一致，改变模式会改变计数轨迹与周期计算。',
'TIM_Period':'100−1即ARR=99，每周期100计数；占空比因此有1%步进；改变ARR需同步频率公式和CCR解释。',
'TIM_Prescaler':'720−1即PSC=719，初始1000Hz；随后按音符频率动态更新；PSC越大，计数时钟越慢。',
'TIM_RepetitionCounter':'0表示重复计数初值；TIM2/3通用定时器不使用高级定时器的重复计数机制，保留标准结构字段。',
'TIM_OCMode':'PWM1，在向上计数中CNT低于CCR时有效；与高极性一起形成高电平脉冲。',
'TIM_OCPolarity':'High表示有效状态输出高电平；改变极性会反转脉冲有效电平。',
'TIM_OutputState':'Enable把比较输出送到通道引脚；关闭时不会输出该PWM。',
'TIM_Pulse':'0即初始CCR=0，上电静音；后续由音色或关闭函数更新。',
}

def inventory():
    data={'functions':[],'locals':[],'config':[],'globals':[],'macros':[]}
    tp=r'(?:uint(?:8|16|32)_t|int(?:8|16|32)_t|int|char|float|double|GPIO_InitTypeDef|TIM_TimeBaseInitTypeDef|TIM_OCInitTypeDef|EXTI_InitTypeDef|NVIC_InitTypeDef|ADC_InitTypeDef)'
    for p in sorted((ROOT/'firmware').rglob('*')):
        rel=p.relative_to(ROOT/'firmware').as_posix()
        if p.suffix!='.c' or not rel.startswith(('User/','Hardware/','System/')):continue
        scope='global'
        for n,l in enumerate(read(p).splitlines(),1):
            c=l.split('//')[0].strip()
            m=re.match(r'('+tp+r'|void)\s+(\w+)\s*\(([^)]*)\)\s*\{?\s*$',c)
            if m:
                scope=m[2];data['functions'].append(dict(file=rel,line=n,name=scope,ret=m[1],params=m[3]))
            d=re.match(r'('+tp+r')\b\s*(\*?\s*\w+)(.*);',c)
            if d and not m and not d[3].lstrip().startswith('('):
                target='globals' if scope=='global' else 'locals'
                data[target].append(dict(file=rel,line=n,scope=scope,type=d[1],name=d[2].strip(),value=d[3].strip()))
            for typ,var,val in re.findall(r'for\s*\(\s*(int|uint8_t|uint16_t)\s+(\w+)\s*=\s*([^;]+)',c):
                data['locals'].append(dict(file=rel,line=n,scope=scope,type=typ,name=var,value=val+'；for循环'))
            cf=re.match(r'(\w+)\.(\w+)\s*=\s*(.*);',c)
            if cf:data['config'].append(dict(file=rel,line=n,scope=scope,instance=cf[1],field=cf[2],value=cf[3]))
            ma=re.match(r'#define\s+(\w+(?:\([^)]*\))?)\s+(.*)',c)
            if ma:data['macros'].append(dict(file=rel,line=n,name=ma[1],value=ma[2]))
    return data

def local_desc(x):
    name=x['name'];scope=x['scope'];v=x['value']
    if name.endswith('InitStructure'):
        return '局部配置结构体；赋值后交给对应的初始化接口写入外设配置，具体字段见下表。'
    if name in ('major','minor','seventh'):return ARRAYS[name]
    if name=='freq':
        if scope=='chord':return 'uint16_t、Hz，初值0；switch按chordType写基础和弦音×根音倍率×八度，再乘全局移调返回。两阶段整数转换影响末位Hz；初值为没有匹配分支时提供确定结果。'
        key={682:5,702:3,725:6,748:7,769:4,787:1,805:2}[x['line']]
        return f'uint16_t、Hz，第{key}琴键在按下时计算；读取scale[{key-1}+sft]、transpose[tsp]、oct、sharp，供Buzzer_ON使用。浮点积转整数后发声；各因子增大使对应音高上移。'
    if name in ('vrX','vrY'):return f'uint16_t，ADC计数0—4095；本函数调用JoyStick_Get{"X" if name=="vrX" else "Y"}后保存快照，与1024/3072比较。数值跨过阈值选择不同和弦；中心区保留现有和弦。'
    if name=='n':return 'int，进入加花时赋i%beat，范围0…beat−1；作为加花循环j的起点，保持当前拍内位置。它在该分支赋值后才读取，其他分支不使用。'
    if name=='psc':return 'uint16_t，写入定时器预分频寄存器的中间值；由720000/freq−1计算并取整。增大psc降低输出频率；freq=1临时复位请求的结果按16位转换为64639。'
    if name=='Result':return 'uint32_t，初值1是乘法单位元；OLED_Pow每轮乘X，循环结束返回。Y=0时直接得1，供数字逐位取数使用。'
    if name=='Number1':return 'uint32_t，符号分支写入Number的非负幅值；数字循环读取其各位。把符号显示与数位计算分开；本应用传入的有符号参数仅为小范围移调/平移值。'
    if scope=='Buzzer_Drum':
        if x['line']==110:return 'int循环计数i，从0到14，共15轮；每轮两次1ms频率片段，共标称30ms。增加轮数会延长小军鼓片段并改变伴奏时间分配。'
        start={126:500,133:400,140:300}[x['line']]
        return f'int i同时表示当前Hz；从{start}递减至{start-29}，每步1ms，共30步。起点决定音区，终止差决定扫描时长，递减步长决定滑落速度。'
    if scope=='introPlay':return 'int子步索引j，从0到beat−1；同时索引两条前奏鼓轨并计算LED拍组。上界由数组长度决定，增大需同步数据长度。'
    if scope=='acmpPlay' and name=='i':return 'int主段索引i，从0到number−1；读取三条主段数组，计算灯光与加花起点。每轮重置0；改变number会改变遍历长度。'
    if scope=='acmpPlay' and name=='j':return 'int加花索引j，从n到beat−1，读取两条加花数组；n由当前i取模得到。加花结束后退出当前主段遍历，下一轮回到主段首项。'
    if scope=='OLED_Clear':return 'uint8_t i,j；j从0到7遍历页，i从0到127遍历列；共同覆盖1024字节。改变上界需与屏幕分辨率和寻址方式一致。'
    if scope=='OLED_Init':return 'uint32_t i,j；各从0到999，两层空循环形成上电等待。1000表示循环次数，等待时间由CPU频率和编译优化共同决定；增大循环次数会增加初始化等待。'
    if scope=='OLED_I2C_SendByte':return 'uint8_t位索引i，0—7；生成0x80>>i掩码，按MSB先行输出。循环8次正好覆盖一个字节；改顺序会改变发送位序。'
    if scope=='OLED_ShowChar':return 'uint8_t i，两次0—7循环分别读字模上半部[i]与下半部[i+8]。每次8字节与8像素字符宽度对应。'
    if scope=='OLED_ShowString':return 'uint8_t字符偏移i，从0起，遇String[i]==0停止；同时决定Column+i和要显示的字符。长度来自字符串终止符，调用者需让文本适配行宽。'
    if scope=='OLED_ShowHexNum':return 'uint8_t i为0…Length−1的数位位置，SingleNumber为当前16进制位0—15。小于10加字符0，否则减10加A；位数增加会占用更多列。'
    if scope in ('OLED_ShowNum','OLED_ShowSignedNum','OLED_ShowBinNum'):return 'uint8_t数位索引i，0…Length−1；决定进制幂Length−i−1和写入列。带符号函数另偏移一列，避免覆盖符号。'
    if scope=='acmp':
        return 'char事件数组；当前风格分支创建，acmpPlay在调用期间只读。完整取值、长度与各元素作用见六套序列表。'
    raise ValueError(('unmapped local',x))

def build():
    inv=inventory();out=[]
    out.append('### A. 状态与基础数据\n')
    rows=[]
    for x in inv['globals']:
        name=x['name'].lstrip('* ').strip()
        if name in GLOBALS:
            typ,rw,desc=GLOBALS[name];rows.append([f'`{name}`',typ,rw,desc,link(x['file'],x['line'])])
    out.append(table(['变量','类型、范围与默认值','读写位置','设置意义与影响','定位'],rows))
    for x in inv['globals']:
        name=x['name'].lstrip('* ').strip()
        if name in ARRAYS:
            out.append(f"#### `{name}`\n\n{ARRAYS[name]} {link(x['file'],x['line'])}\n\n```c\n{x['type']} {x['name']}{x['value']};\n```\n")
    out.append('### B. 每个函数的接口与参数\n\n各函数按模块列出职责、参数和返回值。\n')
    for f in inv['functions']:
        name=f['name'];purpose=PURPOSE.get(name)
        if not purpose:
            if name.startswith('Key_Init'):purpose='按函数对应的GPIO端口配置下拉输入。'
            elif name.startswith('Key_Read'):purpose='读取指定端口引脚；非零返回1，低电平返回0。'
            elif name.startswith('LED_Init'):purpose='配置相应端口推挽输出并置高，初始熄灭。'
            elif name.startswith('LED_ON'):purpose='相应端口输出低电平，点亮低有效LED。'
            elif name.startswith('LED_OFF'):purpose='相应端口输出高电平，熄灭LED。'
            elif name.startswith('PWM_Init'):purpose='配置相应定时器与输出通道；两个初始化函数保持相同计时参数，通道独立。'
            elif name.startswith('PWM_SetDuty'):purpose='更新对应通道比较值，改变占空比。'
            elif name.startswith('PWM_SetFreq'):purpose='由目标频率计算16位PSC，在更新事件时装载。'
            elif name in ('HardFault_Handler','MemManage_Handler','BusFault_Handler','UsageFault_Handler'):purpose='启动向量对应的异常入口，模板实现停留在while(1)，便于调试器定位异常状态。'
            else:purpose='启动向量对应的模板入口，当前函数体为空；SysTick等待采用轮询，不依赖此入口。'
        out.append(f"#### `{name}`\n\n{purpose} {link(f['file'],f['line'])}\n\n```c\n{f['ret']} {name}({f['params']});\n```\n")
        args=[]
        if f['params'] not in ('void',''):
            for arg in f['params'].split(','):
                pa=re.search(r'(\w+)(?:\[\])?\s*$',arg.strip())[1]
                if pa=='number':desc='chord中取0—8：0休止；非零先减1，%4选和弦音、/4选八度。' if name=='chord' else '当前主段事件数，调用值12/16/24/32；决定i循环上界，必须与arp/drums/cymbals的实际长度相同。'
                elif pa in ('X','Y'):
                    if name=='OLED_Pow':desc='uint32_t底数，逐轮乘入Result；用于进制2/10/16。' if pa=='X' else 'uint32_t指数，while(Y--)逐轮减小；传入数位位置，0次幂返回1。'
                    else:desc='像素列0—127；高4位和低4位分别写地址命令，增加1向右移一列。' if pa=='X' else '页号0—7；每页8个像素高，0xB0|Y设置页地址，增加1向下移8像素。'
                else:desc=PARAM[pa]
                args.append([f'`{arg.strip()}`',desc])
            out.append(table(['参数','含义、使用方式与变化影响'],args))
    out.append('### C. 局部变量与配置结构体\n\n变量按函数和声明位置区分；循环变量包含在内。数组谱例另列于F节，避免两次重复铺陈。\n')
    for file in sorted({x['file'] for x in inv['locals']}):
        rows=[]
        for x in inv['locals']:
            if x['file']!=file or (x['scope']=='acmp' and '[' in x['value']):continue
            rows.append([f"`{x['scope']}` / `{x['name']}`",f"`{x['type']}`；{x['value'] or '随后在使用前赋值'}",local_desc(x),link(file,x['line'])])
        out.append(f'#### `{file}`\n'+table(['函数 / 变量','声明或初值','原因、读写及影响','定位'],rows))
    out.append('### D. 外设初始化字段逐项对照\n\nGPIO、ADC、EXTI、NVIC和定时器结构体在本函数中赋值，随后被对应标准库初始化接口读取。相同字段在不同外设、不同次赋值处分别列出。\n')
    for file in sorted({x['file'] for x in inv['config']}):
        rows=[]
        for x in inv['config']:
            if x['file']!=file:continue
            exp=CFG[x['field']]
            if isinstance(exp,dict):exp=exp[x['value']]
            rows.append([f"`{x['scope']}` / `{x['field']}`",f"`{x['value']}`",exp,link(file,x['line'])])
        out.append(f'#### `{file}`\n'+table(['作用域 / 字段','实际值','设置原因与影响','定位'],rows))
    out.append('### E. 宏、字模、寄存器值与界面参数\n')
    rows=[]
    for m in inv['macros']:
        name=m['name']
        desc='GPIOC引脚电平写入封装；x为0/1，分别拉低/释放总线；在开始、停止和字节发送函数读取。' if name.startswith('OLED_') else '把物理引脚位掩码命名为操作部件，主程序和中断逻辑复用；端口由调用GPIOA/GPIOB决定，修改需与接线表同步。'
        rows.append([f'`{name}`',f"`{m['value']}`",desc,link(m['file'],m['line'])])
    out.append(table(['宏','值','含义与影响','定位'],rows))
    out.append('`User/stm32f10x_conf.h` 的 `assert_param(expr)` 根据 `USE_FULL_ASSERT` 选择参数检查或空操作；本工程该检查宏未开启。开启后，失败表达式会调用 `assert_failed(uint8_t *file, uint32_t line)`，其中file和line用于定位源文件与行号，需提供对应处理函数。各头文件的 `__…_H` 宏是包含保护，防止重复声明；工程宏 `USE_STDPERIPH_DRIVER` 引入标准库配置，器件头文件默认选择中容量 `STM32F10X_MD`。\n')
    font=read(ROOT/'firmware/Hardware/OLED_Font.h'); vals=re.findall(r'0x[0-9A-Fa-f]+',font)
    out.append(f'`OLED_F8x16[][16]` 是 `const uint8_t` 字模数组，包含{len(vals)//16}个字形、每字形16字节，总{len(vals)}字节。第一维以 `Char-32` 索引；第二维0—7表示上半部八列，8—15表示下半部八列；每个字节的8位控制该页内纵向像素。每一位对应一个字形像素，置1点亮、置0熄灭。`const` 使字库作为只读数据使用，全部字节可在[字模源文件](firmware/Hardware/OLED_Font.h#L7)中逐项查阅。\n')
    const_rows=[
    ['72 MHz、HSE 8 MHz、PLL×9','系统时钟路径；AHB÷1、APB2÷1、APB1÷2，TIM2/3取72MHz。改变晶振或PLL后必须同步延时及PWM换算。'],
    ['RCC_PCLK2_Div6、ADC_SampleTime_55Cycles5、rank=1','ADC时钟12MHz，采样55.5周期，规则序列第1位。较长采样允许输入采样电容有更多建立时间；缩短采样改变速度与输入稳定性要求。'],
    ['GPIO_PortSource / GPIO_PinSource','将A8/A11/A10、B3/B6/B9/B12/B13/B14/B15映射至同编号EXTI线；编码器将B0/B1映射到0/1线；必须与中断中读取的端口一致。'],
    ['NVIC_PriorityGroup_2','4位优先级分成2位抢占+2位子优先级，各0—3；各初始化使用相同分组。'],
    ['TIM_OCStructInit、TIM_InternalClockConfig','先填充输出比较结构默认值，再覆盖PWM相关字段；定时器以内部时钟驱动计数。'],
    ['TIM_PSCReloadMode_Update、CNT=51','预分频更新模式在更新事件生效；51位于当前最大CCR50之外；复位请求freq=1的16位换算见正文。'],
    ['SysTick LOAD=72×xus、VAL=0','72个72MHz周期约1μs；清VAL从头计数。LOAD具有24位范围，计数含零；公式体现名义微秒尺度。'],
    ['SysTick CTRL=0x5、0x10000、0x4','依次表示启用+HCLK、读取COUNTFLAG、关闭计数但保留HCLK；没有使能TICKINT。'],
    ['1000 / 1000','Delay_ms与Delay_s的单位换算；OLED_Init中的1000×1000表示两层忙等循环次数。'],
    ['30000 / 15000 / 20000','分别来自一分钟60000ms的二分、四分、三分细分。tempo为分母；C整数除法舍弃余数。'],
    ['30 / 60 / 70 / 240 / 500 ms','30为鼓声片段；60为双鼓总占时或尾声单音；70为键盘鼓声附加等待；240为四个60ms尾声位置；500为尾声后收尾等待。'],
    ['200 / 300 ms','主循环功能键操作后的等待；伴奏设置通常200，音色设置部分操作300。按住按键会受轮询与等待影响重复触发；等待增大降低重复频率，也增加操作间隔。'],
    ['1024 / 3072','ADC方向阈值，约四分之一/四分之三量程；中间范围保留和弦。阈值靠近中心会使方向选择更敏感，向两端移动则需要更大摇杆偏转。'],
    ['1.06、2、4、0','1.06近似半音比，2用于八度，4用于和弦音序分组；音符/鼓编码0具有休止含义，音色编号从1开始。'],
    ['0x78 / 0x00 / 0x40','OLED地址写字节、命令控制字、数据控制字；发送地址7位形式为0x3C。控制字0x40与初始化开始行命令0x40在不同位置有不同含义。'],
    ['0x80 >> i；8；0xB0；0x10；0xF0；0x0F；4','MSB优先位掩码、每字节8位、页命令、列高半字节命令、高低半字节掩码和位移4；改变它们会改变总线位序或显示地址。'],
    ['128、8页、8×16、32','屏幕列数、页数、字形宽高、空格ASCII偏移；4行×16列由分辨率和字形尺寸推导。'],
    ['数字进制10/16/2、字符0与A、Length−i−1','从高位到低位提取；十六进制10以上映射A—F；固定长度使显示位置稳定。'],
    ]
    out.append(table(['常量或配置','原因、适用位置与变化影响'],const_rows))
    oledcmd=[('AE','关闭显示','初始化过程中先关闭，随后写各配置，AF恢复显示。'),('D5,80','时钟分频/振荡频率','0x80的低4位为分频设置0，高4位8为振荡设置；影响控制器刷新时序。'),('A8,3F','多路复用率','0x3F表示64路，匹配64像素高度；改变会影响扫描行数。'),('D3,00','显示偏移','0偏移使画面从预期行开始；非零会改变垂直映射。'),('40','显示开始行','命令低6位为0，从第0行开始；与数据控制字的位置不同。'),('A1','段重映射','选择当前左右方向；A0选择相反映射。'),('C8','COM扫描方向','选择当前上下方向；C0选择相反扫描。'),('DA,12','COM引脚配置','0x12选择与此类128×64模块对应的COM排列；需与面板接法匹配。'),('81,CF','对比度','0xCF=207，调整驱动电流相关亮度；增大通常更亮且耗电增加。'),('D9,F1','预充电周期','低半字节1、高半字节15分别表示两阶段周期设置；影响像素驱动建立过程。'),('DB,30','VCOMH去选电平','0x30对应SSD1306命令模型约0.83×VCC；改变影响面板驱动条件。'),('A4','按显示RAM输出','不强制全屏点亮，正常显示写入数据。'),('A6','正常显示','按RAM位显示；A7会反相。'),('8D,14','充电泵','0x14使能充电泵，适合相应供电方式的模块。'),('AF','开启显示','初始化完成后开启，再清屏。')]
    out.append('#### OLED初始化命令序列\n\n按驱动所采用的SSD1306兼容命令模型解释；具体模块的控制器与供电方式需和这些设置对应。[查看OLED_Init](firmware/Hardware/OLED.c#L276)\n'+table(['十六进制字节','用途','设置意义与影响'],oledcmd))
    out.append('#### 界面调用中的位置、长度与文本\n\nLine/Column从1计数，固定空格用于覆盖旧内容；同一调用在多个分支出现时合并列出第一次位置。下表保留每个不同的显示调用，便于复核全部坐标、位数与标签。\n')
    calls={}
    for n,line in enumerate(read(ROOT/'firmware/User/main.c').splitlines(),1):
        m=re.search(r'(OLED_Show\w+)\((.*)\);',line)
        if m:calls.setdefault((m[1],m[2]),n)
    out.append(table(['调用','参数含义','定位'],[(f'`{f}({a})`','前两项是字符行、列；字符串是固定显示内容或状态名称；数值显示最后一项为位数，符号另占一列。空字符串区域以空格清除。',link('User/main.c',n)) for (f,a),n in calls.items()]))
    out.append('### F. 六套伴奏的完整事件序列\n\n每个风格都使用相同的五类数组接口。`arp`中的0为休止，1—8为和弦音序；鼓数组中的0为30ms等待，1—9对应鼓声表。各数组只在当前分支调用期间使用，播放函数不修改内容。\n')
    text=read(ROOT/'firmware/User/main.c')
    styles=[('8Beat',16,8,'250 ms；两组八子步，琶音连续排列'),('16Beat',32,16,'125 ms；两组十六子步，琶音包含上八度音序6'),('Slow Rock',24,12,'166 ms；两组三连音细分序列'),('Swing',12,12,'166 ms标称；琶音含0，实际休止分支按正文的两次等待执行'),('March',32,16,'125 ms标称；交替琶音与0事件，实际时长按分支累计'),('Waltz',12,6,'250 ms；两个三拍分组，每拍两个子步')]
    rows=[]
    for i,(name,num,beat,desc) in enumerate(styles,1):
        a=text.index(f'if(style=={i})');b=text.index('acmpPlay(',a);block=text[a:b];line=text[:a].count('\n')+1
        out.append(f'#### {i}. {name}\n\n`number={num}`，`beat={beat}`；120 BPM下{desc}。{link("User/main.c",line)}\n')
        for m in re.finditer(r'char\s+(\w+)\[(\d+)\]\s*=\s*\{([^}]+)\};',block):
            arr,length,vals=m.groups(); values=[int(v.strip()) for v in vals.split(',')]
            assert len(values)==int(length)
            exp={'arp':'和弦音顺序；提高音序可以进入更高八度，0进入休止分支。','drums':'第一鼓轨，每项决定当前鼓声频率/扫描形状。','cymbals':'第二鼓轨，仅track=1时用于主段。','fillDrums':'前奏及加花第一鼓轨，beat项覆盖一组。','fillCymbals':'前奏及加花第二鼓轨，与第一轨逐项配对。'}[arr]
            arrline=text[:a+m.start()].count('\n')+1
            out.append(f'**`{arr}[{length}]`**：{exp} {link("User/main.c",arrline)}\n\n```c\n{{{", ".join(map(str,values))}}}\n```\n')
            rows.append({'style':name,'array':arr,'length':int(length),'values':values})
    out.append('### G. 启动、时钟与标准库调用链\n')
    out.append(table(['层次','当前设置','作用与更改影响'],[
    ['启动栈与堆','startup_stm32f10x_md.s：Stack_Size=0x400；Heap_Size=0x200','分别为1024与512字节，8字节对齐；栈容纳函数局部变量、调用与异常现场；堆为运行库动态分配预留。增加会提高RAM静态预留，容量判断需结合调用深度。'],
    ['复位入口','Reset_Handler → SystemInit → __main → main','先建立系统时钟，运行库初始化数据与C环境，再进入应用；文件选择需匹配中容量器件向量。'],
    ['时钟变量','SystemCoreClock=72000000','全局uint32_t，SystemCoreClockUpdate可按寄存器重新计算；本应用不调用该更新函数，PWM/Delay使用固定72MHz公式。'],
    ['时钟表','AHBPrescTable[16]={0,0,0,0,0,0,0,0,1,2,3,4,6,7,8,9}','CMSIS系统文件把HPRE编码映射为右移位数；属于厂商时钟计算实现，用于把系统时钟换成HCLK。'],
    ['HSE启动与Flash','HSE_VALUE=8000000；HSE_STARTUP_TIMEOUT=0x0500；72MHz路径Flash等待2周期','HSE启动计数上限是轮询次数；等待周期配合系统频率，APB1分频2使其为36MHz；时钟源和等待配置共同决定运行条件。'],
    ['RCC/GPIO/AFIO','ClockCmd、GPIO_Init、GPIO_EXTILineConfig、GPIO_PinRemapConfig','先打开外设时钟，再设置引脚与EXTI映射；寄存器访问由ST库封装。'],
    ['定时器','TIM_TimeBaseInit、TIM_OC1Init/OC2Init、TIM_Cmd、TIM_SetCompare、TIM_PrescalerConfig','建立周期和输出比较，后续以CCR/PSC更新声音；SetCounter仅修改当前计数位置。'],
    ['ADC','ADC_Init、ADC_Cmd、校准、RegularChannelConfig、SoftwareStartConvCmd、GetFlagStatus、GetConversionValue','顺序建立转换条件、选择通道、触发、等待并读取；更换通道与读取顺序由JoyStick接口组织。'],
    ['EXTI/NVIC','EXTI_Init、NVIC_Init、EXTI_GetITStatus、EXTI_ClearITPendingBit','线触发与CPU调度分开配置；ISR检查标志并在处理后清除。'],
    ['工程选项','ARMCC 5.06u5；uAC6=0；uC99=1；Optim字段1；wLevel字段2','使用ARMCC5工具链并开启C99，允许for中的局部变量声明；优化与警告枚举保留原设置，工具链变化后重新构建验证。'],
    ['构建输出','OutputDirectory=.\\Objects\\；OutputName=Project；CreateHexFile=0','构建产物写入Objects，原设置不额外导出HEX；带调试信息的AXF可用于调试下载，需要HEX文件时应明确开启该输出。'],
    ['调试信息','DebugInformation=1；BrowseInformation=1','生成调试符号与浏览信息，便于变量检查及源码定位。'],
    ]))

    p=ROOT/'电子琴设计_技术文档.md';base=p.read_text(encoding='utf-8').split('<!-- GENERATED_APPENDIX -->')[0]
    p.write_text(base+'<!-- GENERATED_APPENDIX -->\n\n'+'\n'.join(out),encoding='utf-8')
    return inv,rows
if __name__=='__main__':
    inv,seq=build();print(json.dumps({k:len(v) for k,v in inv.items()},ensure_ascii=False))
