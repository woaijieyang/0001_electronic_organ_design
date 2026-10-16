"""Source-derived illustrations. No measured performance data is implied."""
from pathlib import Path
import sys, json, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parents[1];F=R/'assets/figures'
# Use the requested skill when available, with a portable equivalent fallback.
skill=Path.home()/'.codex/skills/scipilot-figure-skill/scripts'
if skill.exists():
 sys.path.insert(0,str(skill))
 from setup_style import setup_style
 setup_style(journal='general',lang='zh',use_sciplots=False)
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'font.size':12,'axes.titlesize':15,'axes.labelsize':12,'xtick.labelsize':11,'ytick.labelsize':11,'legend.fontsize':11,'axes.unicode_minus':False,'svg.fonttype':'path','figure.facecolor':'#fffdf9','axes.facecolor':'#fffdf9','axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#969094','text.color':'#292830','axes.labelcolor':'#292830','grid.alpha':.17})
red='#8f1d2c';blue='#326583';gold='#9b7629'
def save(fig,name):
 fig.canvas.draw()
 if skill.exists():
  try:
   from visual_qa import audit_layout
   print(name,audit_layout(fig))
  except (ImportError,AttributeError) as e:print('Optional layout helper',type(e).__name__)
 fig.savefig(F/(name+'.svg'),bbox_inches='tight')
 fig.savefig(F/(name+'.png'),dpi=180,bbox_inches='tight')
 plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(11,4.6),layout='constrained')
freq=np.array([524,588,660,698,784,880,988]);x=np.arange(1,8)
axs[0].scatter(x,freq,s=58,color=red,zorder=3)
for i,y in zip(x,freq):axs[0].annotate(str(y),(i,y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=10)
axs[0].set(xlabel='琴键位置',ylabel='请求频率 / Hz',xticks=x,ylim=(450,1090),title='a  默认七键：sft=3，oct=1')
t=np.arange(-5,7);v=np.array([.75,.79,.84,.89,.94,1,1.06,1.12,1.19,1.26,1.33,1.41])
axs[1].plot(t,2**(t/12),'--',color=blue,label='十二平均律理论倍率')
axs[1].scatter(t,v,color=red,marker='s',s=28,label='源码查表倍率',zorder=3)
axs[1].set(xlabel='界面移调值 / 半音',ylabel='频率倍率',xticks=[-5,-3,-1,0,2,4,6],title='b  移调以倍率表示');axs[1].legend(loc='upper left')
for ax in axs:ax.grid(axis='y')
save(fig,'pitch')

fig,axs=plt.subplots(5,1,figsize=(10,6),sharex=True,layout='constrained')
t=np.linspace(0,2,2001)
for ax,d in zip(axs,[50,40,30,20,10]):
 y=(t%1<d/100).astype(float);ax.step(t,y,where='post',color=red,lw=1.6);ax.fill_between(t,y,step='post',color=red,alpha=.07)
 ax.set(ylim=(-.15,1.35),yticks=[0,1],ylabel=f'{d}%');ax.spines['left'].set_visible(False)
axs[0].set_title('同一周期，不同脉冲宽度',loc='left');axs[-1].set(xlabel='时间 / 周期 T',xticks=[0,.5,1,1.5,2],xlim=(0,2))
save(fig,'pwm')

fig,axs=plt.subplots(2,1,figsize=(10,5.6),layout='constrained')
t=np.arange(31);y=np.where(t%2==0,600,1200);axs[0].step(t,y,where='post',color=red,lw=1.6);axs[0].set(title='a  小军鼓：600 / 1200 Hz 交替，15 轮',ylabel='请求频率 / Hz',xlim=(0,30),ylim=(500,1330),xticks=[0,5,10,15,20,25,30])
for start,marker,c in [(500,'o',red),(400,'s',blue),(300,'^',gold)]:
 axs[1].step(np.arange(31),np.r_[np.arange(start,start-30,-1),start-29],where='post',color=c,label=f'{start} → {start-29} Hz')
 axs[1].scatter([0,15,29],[start,start-15,start-29],marker=marker,color=c,s=22)
axs[1].set(title='b  通鼓：每毫秒下降 1 Hz，共 30 个台阶',xlabel='标称片段时间 / ms',ylabel='请求频率 / Hz',xlim=(0,30),ylim=(250,550));axs[1].legend(loc='upper right',ncol=3)
for ax in axs:ax.grid(axis='y')
save(fig,'drums')

fig,ax=plt.subplots(figsize=(10,4.7),layout='constrained');bpm=np.arange(40,241)
for k,label,c,ls in [(30000,'beat=6 / 8：八分细分',red,'-'),(20000,'beat=12：三连音细分',blue,'--'),(15000,'beat=16：十六分细分',gold,':')]:
 ax.plot(bpm,k//bpm,c=c,ls=ls,lw=2,label=label)
ax.set(xlabel='速度 / BPM',ylabel='标称单步时长 / ms',xlim=(40,240),ylim=(0,800),xticks=[40,80,120,160,200,240],title='速度越快，每一个子步分配的时间越短');ax.legend(loc='upper right');ax.grid();save(fig,'tempo')
print('4 numeric figures generated')
