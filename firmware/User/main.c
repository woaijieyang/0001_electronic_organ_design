#include "stm32f10x.h"                  // Device head
#include <math.h>

#include "Delay.h"
#include "LED.h"
#include "Key.h"
#include "Buzzer.h"
#include "OLED.h"
#include "Encoder.h"
#include "Keyboard.h"
#include "JoyStick.h"

#define Key1 GPIO_Pin_10  //屏幕下方左键，接A10和正极
#define Key2 GPIO_Pin_15  //屏幕下方中键，接B15和正极
#define Key3 GPIO_Pin_14  //屏幕下方右键，接B14和正极
#define Key4 GPIO_Pin_9   //旋转编码器按键，接A9和正极
#define LED1 GPIO_Pin_6   //第一颗LED，负极接A6，另一端接正极
#define LED2 GPIO_Pin_4   //第二颗LED，负极接A4，另一端接正极
#define LED3 GPIO_Pin_2   //第三颗LED，负极接A2，另一端接正极

uint8_t voice = 1;      //音色编号
uint8_t knob = 1;       //旋钮功能编号
uint8_t tsp = 5;        //移调参数，范围0至11，屏幕显示为-5至+6
uint8_t sft = 3;        //键盘平移参数，范围0至6，屏幕显示为-3至+3
uint8_t oct = 1;        //八度参数，0：低八度、1：正常、2：高八度
uint8_t sharp = 0;      //升半音参数，0：关、1：开
uint8_t mode = 1;       //模式编号，1：音色模式、2：伴奏模式
uint8_t style = 1;      //伴奏风格编号
uint16_t tempo = 120;   //速度，单位为bpm
uint8_t chordType = 0;  //和弦类型
uint8_t isPlaying = 0;  //伴奏是否在播放，0：不在播放、1：在播放
uint8_t track = 0;      //音轨开关状态，0：鼓1轨和琶音轨、1：鼓1轨和鼓2轨、2：琶音轨
uint8_t section = 0;    //前奏尾声段落开关状态，0：前奏和尾声、1：前奏、2：尾声、3：关闭
uint8_t arpVoice = 1;   //琶音音色编号

/* 大调音阶频率       G   A   B   C   D   E   F   G   A   B   C   D   E   */
uint16_t scale[] = {196,220,247,262,294,330,349,392,440,494,523,587,659};

/* 移调系数           -5   -4   -3   -2   -1   0   +1   +2   +3   +4   +5   +6   */
float transpose[] = {0.75,0.79,0.84,0.89,0.94,1.0,1.06,1.12,1.19,1.26,1.33,1.41};
//频率的比例关系大致是固定的（约为 1.06 倍，即 2 的 1/12 次方）

/* 音色方波占空比 */
uint8_t voiceDuties[5] = {50,40,30,20,10};

/* OLED显示屏显示信息 */
char* voiceNames[6] = {"Clarinet","Pipe Organ","Accordion","Oboe","Trumpet","Drums"};
char* styleNames[6] = {"8Beat","16Beat","Slow Rock","Swing","March","Waltz"};
char* trackStatus[3] = {"Dr&Ap","Drums","Arpgo"};
char* sectionStatus[4] = {"In&Ed","Intro","Endng"," OFF "};
char* chordNames[8] = {"C ","Dm","Em","E7","F ","G ","G7","Am"};


/**
  * @brief  和弦音符频率生成函数，用于伴奏琶音播放，和弦类型由全局变量chordType决定
  * @param  number：和弦的第几个音，1至4为和弦的第1至第4个音，5至8算做高八度的1至4
  * @retval 和弦音符频率
  */
int chord(char number){
	uint16_t freq = 0;
  if(number == 0){
    return 0;
  }
  uint16_t major[] = {131,165,196,262};    //大三和弦1、3、5、1
  uint16_t minor[] = {131,156,196,262};    //小三和弦1、b3、5、1
  uint16_t seventh[] = {131,165,196,233};  //属七和弦1、3、5、b7
  number = number - 1;
  switch(chordType){
    case 0:  //C
			freq = major[number%4]*pow(2,number/4);
			break;
    case 1:  //Dm
			freq = minor[number%4]*pow(2,number/4)*transpose[7];
			break;
    case 2:  //Em
			freq = minor[number%4]*pow(2,number/4)*transpose[9];
			break;
    case 3:  //E7
			freq = seventh[number%4]*pow(2,number/4)*transpose[9];
			break;
    case 4:  //F
			freq = major[number%4]*pow(2,number/4)*transpose[10];
			break;
    case 5:  //G
			freq = major[number%4]*pow(2,number/4)*transpose[0];
			break;
    case 6:  //G7
			freq = seventh[number%4]*pow(2,number/4)*transpose[0];
			break;
    case 7:  //Am
			freq = minor[number%4]*pow(2,number/4)*transpose[2];
			break;
  }
  return freq*transpose[tsp];
}


/**
  * @brief  前奏播放函数
  * @param  introDrums[]：前奏鼓点1轨的数组
  * @param  introCymbals[]：前奏鼓点2轨的数组
	*	@param	beat：前奏的节拍，
	*								6表示以8分音符量化的3/4拍，
	*								8表示以8分音符量化的4/4拍，
	*								16表示以16分音符量化的4/4拍，
	*								12表示以三连音音符量化的6/8拍
  * @retval 无
  */
void introPlay(char introDrums[],char introCymbals[],char beat){
	isPlaying = 1;
	OLED_ShowString(2,12,"     ");
	OLED_ShowString(4,1,"OctDw OctUp Shrp");
	if(section == 0 || section == 1){
		OLED_ShowString(3,1,"Intro           ");
		for(int j=0;j<beat;j++){
			if(beat==6){
				switch(j/2%3){
					case 0:
						LED_ON_A(LED1|LED2);
						break;
					case 1:
						LED_ON_A(LED2|LED3);
						break;
					case 2:
						LED_ON_A(LED1|LED3);
						break;
				}
			}
			else{
				switch(j/(beat/4)%4){
					case 0:
						LED_ON_A(LED1|LED2|LED3);
						break;
					case 1:
						LED_ON_A(LED1);
						break;
					case 2:
						LED_ON_A(LED2);
						break;
					case 3:
						LED_ON_A(LED3);
						break;
				}
			}
			if(track == 0 || track == 1){
				Buzzer_Drum(introDrums[j]);
				Buzzer_Drum(introCymbals[j]);
			}
			else{
				Delay_ms(60);
			}
			switch(beat){
				case 6:
					Delay_ms(30000/tempo-60);
					break;
				case 8:
					Delay_ms(30000/tempo-60);
					break;
				case 12:
					Delay_ms(20000/tempo-60);
					break;
				case 16:
					Delay_ms(30000/(tempo*2)-60);
					break;	
			}
			Buzzer_OFF(2);
			LED_OFF_A(LED1|LED2|LED3);
			if(Encoder_Get() != 0){
				tempo = Encoder_Var(tempo,5,40,240,40,240);
				OLED_ShowNum(2,8,tempo,3);
			}
		}
	}
}


/**
  * @brief  尾声播放函数
  * @param  无
  * @retval 无
  */
void endingPlay(void){
	if(section == 0 || section == 2){
		if(track != 1){
			OLED_ShowString(3,1,"Ending Chord:   ");
			OLED_ShowString(3,15,chordNames[chordType]);
			uint16_t vrX = JoyStick_GetX();
			uint16_t vrY = JoyStick_GetY();
			if(vrX<1024 && vrY<1024){  // 左下 Dm和弦
				chordType = 1;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrX>3072 && vrY<1024){  // 左上 E7和弦
				chordType = 3;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrX<1024 && vrY>3072){  // 右下 Am和弦
				chordType = 7;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrX>3072 && vrY>3072){  // 右上 G和弦
				chordType = 5;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrX<1024){  // 下 C和弦
				chordType = 0;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrX>3072){  // 上 F和弦
				chordType = 4;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrY<1024){  // 左 Em和弦
				chordType = 2;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
			else if(vrY>3072){  // 右 G7和弦
				chordType = 6;
				OLED_ShowString(3,15,chordNames[chordType]);
			}
		}
		else{
			OLED_ShowString(3,1,"Ending          ");
		}
		if(track != 2){
			Buzzer_Drum(1);
			Buzzer_Drum(4);
		}
		if(track != 1){
			Buzzer_Timing(chord(1),60,voiceDuties[arpVoice-1],2);
			Buzzer_Timing(chord(2),60,voiceDuties[arpVoice-1],2);
			Buzzer_Timing(chord(3),60,voiceDuties[arpVoice-1],2);
			Buzzer_Timing(chord(4),60,voiceDuties[arpVoice-1],2);
		}
		else{
			Delay_ms(240);
		}
		Buzzer_OFF(2);
	}
	Delay_ms(500);
	isPlaying = 0;
	OLED_ShowString(3,1,"                ");
	OLED_ShowString(4,1,"                ");
}


/**
  * @brief  伴奏播放函数
  * @param  arp[]：伴奏琶音轨的数组
  * @param  drums[]：伴奏鼓点1轨的数组
  * @param  cymbals[]：伴奏鼓点2轨的数组，仅在关闭琶音轨时发声
  * @param  fillDrums[]：加花鼓点1轨的数组
  * @param  fillCymbals[]：加花鼓点2轨的数组
	*	@param	number：伴奏数组大小，需为beat的整数倍
	*	@param	beat：伴奏的节拍，
	*								6表示以8分音符量化的3/4拍，
	*								8表示以8分音符量化的4/4拍，
	*								16表示以16分音符量化的4/4拍，
	*								12表示以三连音音符量化的6/8拍
  * @retval 无
  */
void acmpPlay(char arp[],char drums[],char cymbals[],char fillDrums[],char fillCymbals[],char number,char beat){
  int n;
	introPlay(fillDrums,fillCymbals,beat);  
	if(track != 1){
		OLED_ShowString(3,1,"Main   Chord:   ");
		OLED_ShowString(3,15,chordNames[chordType]);
	}
	else{
		OLED_ShowString(3,1,"Main            ");
	}
  while(1){
		for(int i=0;i<number;i++){
			
			/* 和弦识别代码 */
			if(track != 1){
				uint16_t vrX = JoyStick_GetX();
				uint16_t vrY = JoyStick_GetY();
				if(vrX<1024 && vrY<1024){  // 左下 Dm和弦
					chordType = 1;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrX>3072 && vrY<1024){  // 左上 E7和弦
					chordType = 3;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrX<1024 && vrY>3072){  // 右下 Am和弦
					chordType = 7;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrX>3072 && vrY>3072){  // 右上 G和弦
					chordType = 5;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrX<1024){  // 下 C和弦
					chordType = 0;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrX>3072){  // 上 F和弦
					chordType = 4;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrY<1024){  // 左 Em和弦
					chordType = 2;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else if(vrY>3072){  // 右 G7和弦
					chordType = 6;
					OLED_ShowString(3,15,chordNames[chordType]);
				}
			}
			
			/* 加花代码 */
			if(JoyStick_GetSW()){
				OLED_ShowString(3,1,"Fill In         ");
				n = i%beat;
				for(int j=n;j<beat;j++){
					if(beat==6){
						switch(j/2%3){
							case 0:
								LED_ON_A(LED1|LED2|LED3);
								break;
							case 1:
								LED_ON_A(LED2);
								break;
							case 2:
								LED_ON_A(LED3);
								break;
						}
					}
					else{
						switch(j/(beat/4)%4){
							case 0:
								LED_ON_A(LED1|LED2|LED3);
								break;
							case 1:
								LED_ON_A(LED1);
								break;
							case 2:
								LED_ON_A(LED2);
								break;
							case 3:
								LED_ON_A(LED3);
								break;
						}
					}
					if(track == 0 || track == 1){
						Buzzer_Drum(fillDrums[j]);
						Buzzer_Drum(fillCymbals[j]);
					}
					else{
						Delay_ms(60);
					}
					switch(beat){
						case 6:
							Delay_ms(30000/tempo-60);
							break;
						case 8:
							Delay_ms(30000/tempo-60);
							break;
						case 16:
							Delay_ms(30000/(tempo*2)-60);
							break;
						case 12:
							Delay_ms(20000/tempo-60);
							break;
					}
					Buzzer_OFF(2);
					LED_OFF_A(LED1|LED2|LED3);
					if(Encoder_Get() != 0){
						tempo = Encoder_Var(tempo,5,40,240,40,240);
						OLED_ShowNum(2,8,tempo,3);
					}
					if(Key_Read_A(Key4)){
						break;
					}
				}
				if(track != 1){
					OLED_ShowString(3,1,"Main   Chord:   ");
					OLED_ShowString(3,15,chordNames[chordType]);
				}
				else{
					OLED_ShowString(3,1,"Main            ");
				}
				break;
			}
			
			/* 节拍指示灯代码 */
			if(beat==6){
				switch(i/2%3){
					case 0:
						LED_ON_A(LED1|LED2|LED3);
						break;
					case 1:
						LED_ON_A(LED2);
						break;
					case 2:
						LED_ON_A(LED3);
						break;
				}
			}
			else{
				switch(i/(beat/4)%4){
					case 0:
						LED_ON_A(LED1|LED2|LED3);
						break;
					case 1:
						LED_ON_A(LED1);
						break;
					case 2:
						LED_ON_A(LED2);
						break;
					case 3:
						LED_ON_A(LED3);
						break;
				}
			}
			
			/* 伴奏播放代码 */
			if(track != 2){
				Buzzer_Drum(drums[i]);
			}
			else{
				Delay_ms(30);
			}
			if(track == 1){
				Buzzer_Drum(cymbals[i]);
				switch(beat){
					case 6:
						Delay_ms(30000/tempo-60);
						break;
					case 8:
						Delay_ms(30000/tempo-60);
						break;
					case 16:
						Delay_ms(30000/(tempo*2)-60);
						break;
					case 12:
						Delay_ms(20000/tempo-60);
						break;
				}
			}
			else{
				if(arp[i] != 0){
					switch(beat){
						case 6:
							Buzzer_Timing(chord(arp[i]),30000/tempo-30,voiceDuties[arpVoice-1],2);
							break;
						case 8:
							Buzzer_Timing(chord(arp[i]),30000/tempo-30,voiceDuties[arpVoice-1],2);
							break;
						case 16:
							Buzzer_Timing(chord(arp[i]),30000/(tempo*2)-30,voiceDuties[arpVoice-1],2);
							break;
						case 12:
							Buzzer_Timing(chord(arp[i]),20000/tempo-30,voiceDuties[arpVoice-1],2);
							break;
					}
				}
				else{
						switch(beat){
						case 6:
							Delay_ms(30000/tempo-30);
							Delay_ms(30000/tempo-30);
							break;
						case 8:
							Delay_ms(30000/tempo-30);
							Delay_ms(30000/tempo-30);
							break;
						case 16:
							Delay_ms(30000/(tempo*2)-30);
							Delay_ms(30000/tempo-30);
							break;
						case 12:
							Delay_ms(20000/tempo-30);
							Delay_ms(30000/tempo-30);
							break;
					}
				}
			}
			Buzzer_OFF(2);
			LED_OFF_A(LED1|LED2|LED3);
			if(Encoder_Get() != 0){
				tempo = Encoder_Var(tempo,5,40,240,40,240);
				OLED_ShowNum(2,8,tempo,3);
			}
			if(Key_Read_A(Key4)){
				break;
			}
		}
		if(Key_Read_A(Key4)){
			endingPlay();
			break;
		}
  }
}


/**
  * @brief  伴奏启动函数,输入编号以启动对应风格的伴奏
  * @param  style：伴奏风格编号
  * @retval 无
  */
void acmp(char style){
  if(style==1){  // 8Beat
		char arp[16] = {4,2,3,2,4,3,2,3,1,2,3,2,4,2,3,2};
		char drums[16]={1,3,2,1,1,3,2,3,1,3,2,1,1,3,2,1};
		char cymbals[16]={3,0,3,3,3,0,3,0,3,0,3,3,3,0,3,3};
		char fillDrums[8]={1,2,2,2,2,2,2,2};
		char fillCymbals[8]={3,3,3,4,5,5,6,7};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,16,8);
  }
  
  if(style==2){  // 16Beat
	char arp[32] = {1,2,3,4,6,4,3,2,1,2,3,4,6,4,3,2,1,2,3,4,6,4,3,2,4,3,2,1,3,2,1,2};
    char drums[32]={1,3,3,3,2,3,3,1,1,3,3,3,2,3,3,1,1,3,3,3,2,3,3,1,1,3,1,3,2,1,3,4};
	char cymbals[32]={3,0,0,0,3,0,0,3,3,0,0,0,3,0,0,3,3,0,0,0,3,0,0,3,3,0,3,0,3,3,0,0};
    char fillDrums[16]={1,0,0,0,2,0,2,2,1,2,0,2,5,5,6,7};
    char fillCymbals[16]={3,3,3,3,3,3,3,3,4,0,0,0,0,0,0,0};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,32,16);
  }

  if(style==3){  // Slow Rock
	char arp[24] = {1,2,3,4,3,2,1,2,3,4,3,2,1,2,3,4,3,2,4,3,2,3,2,3};
    char drums[24]={1,3,3,2,3,1,1,3,3,2,3,3,1,3,3,2,3,1,1,3,3,2,3,1};
	char cymbals[24]={3,0,0,3,0,3,3,0,0,3,0,0,3,0,0,3,0,3,3,0,0,3,0,4};
	char fillDrums[12]={1,0,0,2,0,2,1,2,2,5,6,7};
    char fillCymbals[12]={3,3,3,3,3,3,4,0,0,0,0,0};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,24,12);
  }
  
	if(style==4){  // Swing
	char arp[12] = {5,0,0,6,0,4,3,0,0,6,0,3};
    char drums[12]={1,0,0,2,0,0,1,0,0,2,0,0};
    char cymbals[12]={4,0,0,3,0,4,4,0,0,3,0,4};
	char fillDrums[12]={1,0,0,2,0,2,1,2,2,5,6,7};
    char fillCymbals[12]={4,0,0,3,0,4,4,0,0,0,0,0};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,12,12);
  }
	
	if(style==5){  // March
	char arp[32] = {1,0,6,0,3,0,6,0,1,0,6,0,3,0,6,0,1,0,6,0,3,0,6,0,1,0,5,4,5,0,5,0};
    char drums[32]={1,0,2,0,1,0,2,0,1,0,2,0,1,0,2,0,1,0,2,0,1,0,2,0,1,0,2,2,2,0,2,0};
    char cymbals[32]={3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,3,0,4,0};
    char fillDrums[16]={1,0,2,2,1,0,1,0,1,2,2,2,2,0,2,2};
    char fillCymbals[16]={4,0,3,0,4,0,4,0,4,0,3,0,3,0,4,0};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,32,16);
  }
	
  if(style==6){  // Waltz
	char arp[12] = {1,2,3,2,3,2,4,2,3,2,3,2};
    char drums[12]={1,0,2,0,2,0,1,0,2,0,2,0};
	char cymbals[12]={3,3,4,3,4,3,3,3,4,3,4,3};
    char fillDrums[6]={1,2,2,0,2,2};
    char fillCymbals[6]={3,3,3,3,4,0};
    acmpPlay(arp,drums,cymbals,fillDrums,fillCymbals,12,6);
  }
}



/* 主程序 */
int main(void){
	
	/* 初始化 */
	LED_Init_A(LED1|LED2|LED3);//三颗LED，从左到右负极依次接A6、A4、A2，另一端接正极
	Key_Init_A(Key1|Key4);     //屏幕下方左键和旋转编码器按键，分别接A10和A9，另一端接正极
	Key_Init_B(Key2|Key3);     //屏幕下方中键和右键，分别接B15和B14，另一端接正极
	Buzzer_Init();             //两个扬声器，正极分别接A0和A7，另一端接负极
	OLED_Init();               //OLED显示屏（4针型），SCL接C15，SDA接C14
	Encoder_Init();            //旋转编码器，A接B1，B接B0
	Keyboard_Init();           //七个琴键，从左到右依次接B12、B13、A8、A11、B3、B6、B9，另一端接正极
	JoyStick_Init();           //PS2摇杆模块，VRX接A5，VRY接A3，SW接A1
	
	while(1){
		
		/* 音色模式 */
		if(mode == 1){
			OLED_ShowNum(1,1,voice,1);
			OLED_ShowString(1,3,voiceNames[voice-1]);
			OLED_ShowString(2,1,"Tsp: ");
			OLED_ShowSignedNum(2,6,tsp-5,1);
			OLED_ShowString(2,8,"  Sft: ");
			OLED_ShowSignedNum(2,15,sft-3,1);
			OLED_ShowString(3,11,"M: Voc");
			OLED_ShowString(4,1,"OctDw OctUp Shrp");
			if(Key_Read_A(Key4)){
				knob = Key_Var_Plus(knob,1,3,1);
				Delay_ms(300);
			}
			if(JoyStick_GetSW()){
				mode = Key_Var_Plus(mode,1,2,1);
				knob = 1;
				if(voice == 6){
					voice = 1;
				}
				Delay_ms(300);
				OLED_Clear();
			}
			if(knob == 1){
				OLED_ShowString(3,1,"K: Voice  ");
				if(Encoder_Get() != 0){
					voice = Encoder_Var(voice,1,1,6,6,1);
					OLED_ShowString(1,3,"              ");
				}
			}
			else if(knob == 2){
				OLED_ShowString(3,1,"K: Transp ");
				tsp = Encoder_Var(tsp,1,0,11,0,11);
			}
			else if(knob == 3){
				OLED_ShowString(3,1,"K: Shift  ");
				sft = Encoder_Var(sft,1,0,6,0,6);
			}
		}
		
		/* 伴奏模式 */
		else if(mode == 2){
			OLED_ShowNum(1,1,style,1);
			OLED_ShowString(1,3,styleNames[style-1]);
			OLED_ShowString(2,1,"Tempo: ");
			OLED_ShowNum(2,8,tempo,3);
			OLED_ShowString(2,11," ArpV");
			OLED_ShowNum(2,16,arpVoice,1);
			OLED_ShowString(3,11,"M: Sty");
			OLED_ShowString(4,1,"Play ");
			OLED_ShowString(4,6,trackStatus[track]);
			OLED_ShowString(4,12,sectionStatus[section]);
			if(Key_Read_A(Key1)){
				Delay_ms(200);
				acmp(style);
			}
			if(Key_Read_B(Key2)){
				track = Key_Var_Plus(track,1,2,0);
				Delay_ms(200);
			}
			if(Key_Read_B(Key3)){
				section = Key_Var_Plus(section,1,3,0);
				Delay_ms(200);
			}
			if(Key_Read_A(Key4)){
				knob = Key_Var_Plus(knob,1,3,1);
				Delay_ms(200);
			}
			if(JoyStick_GetSW()){
				mode = Key_Var_Plus(mode,1,2,1);
				knob = 1;
				Delay_ms(200);
				OLED_Clear();
			}
			if(knob == 1){
				OLED_ShowString(3,1,"K: Style  ");
				if(Encoder_Get() != 0){
					style = Encoder_Var(style,1,1,6,6,1);
					OLED_ShowString(1,3,"              ");
				}
			}
			else if(knob == 2){
				OLED_ShowString(3,1,"K: Tempo  ");
				tempo = Encoder_Var(tempo,5,40,240,40,240);
			}
			else if(knob == 3){
				OLED_ShowString(3,1,"K: ArpVoc ");
				arpVoice = Encoder_Var(arpVoice,1,1,5,5,1);
			}
		}
	}
}



/* 键盘弹奏中断函数 */
void EXTI3_IRQHandler(void){
	if(EXTI_GetITStatus(EXTI_Line3) == SET){  // 琴键5
		if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_3)==1){  //如果按下琴键
			if(voice == 6){  //如果音色设置为鼓组
				Buzzer_Drum(5);
				Delay_ms(70);
			}
			else{  //如果音色设置为旋律音色
				Buzzer_Reset(1);
				uint16_t freq = scale[4+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{  //如果松开琴键
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line3);
	}
}

void EXTI9_5_IRQHandler(void){
	if(EXTI_GetITStatus(EXTI_Line8) == SET){  // 琴键3
		if(GPIO_ReadInputDataBit(GPIOA, GPIO_Pin_8)==1){
			if(voice == 6){
				Buzzer_Drum(3);
				Delay_ms(70);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[2+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line8);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line6) == SET){  // 琴键6
		if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_6)==1){
			if(voice == 6){
				if(sharp == 1){
					Buzzer_Drum(8);
				}
				else{
					Buzzer_Drum(6);
				}
				Delay_ms(70);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[5+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line6);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line9) == SET){  // 琴键7
		if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_9)==1){
			if(voice == 6){
				if(sharp == 1){
					Buzzer_Drum(9);
				}
				else{
					Buzzer_Drum(7);
				}
				Delay_ms(70);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[6+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line9);
	}
}

void EXTI15_10_IRQHandler(void){
	if(EXTI_GetITStatus(EXTI_Line11) == SET){  // 琴键4
		if(GPIO_ReadInputDataBit(GPIOA, GPIO_Pin_11)==1){
			if(voice == 6){
				Buzzer_Drum(4);
				Delay_ms(70);
				Buzzer_OFF(2);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[3+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line11);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line12) == SET){  // 琴键1
		if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_12)==1){
			if(voice == 6){
				Buzzer_Drum(1);
				Delay_ms(70);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[0+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line12);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line13) == SET){  // 琴键2
		if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_13)==1){
			if(voice == 6){
				Buzzer_Drum(2);
				Delay_ms(70);
			}
			else{
				Buzzer_Reset(1);
				uint16_t freq = scale[1+sft]*transpose[tsp]*pow(2,oct)*pow(1.06,sharp);
				Buzzer_ON(freq,voiceDuties[voice-1],1);
			}
		}
		else{
			Buzzer_OFF(1);
		}
		EXTI_ClearITPendingBit(EXTI_Line13);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line10) == SET){  // 屏幕下方左键（降低八度键）
		if(mode == 1 || isPlaying == 1){  //仅当设置为音色模式或伴奏正在播放时
			if(GPIO_ReadInputDataBit(GPIOA, GPIO_Pin_10)==1){
				oct = 0;
			}
			else{
				oct = 1;
			}
		}
		EXTI_ClearITPendingBit(EXTI_Line10);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line15) == SET){  // 屏幕下方中键（升高八度键）
		if(mode == 1 || isPlaying == 1){
			if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_15)==1){
				oct = 2;
			}
			else{
				oct = 1;
			}
		}
		EXTI_ClearITPendingBit(EXTI_Line15);
	}
	
	else if(EXTI_GetITStatus(EXTI_Line14) == SET){  // 屏幕下方右键（升高半音键）
		if(mode == 1 || isPlaying == 1){
			if(GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_14)==1){
				sharp = 1;
			}
			else{
				sharp = 0;
			}
		}
		EXTI_ClearITPendingBit(EXTI_Line14);
	}
}
