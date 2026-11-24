import csv,json,math,re,random
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'reports'; OUT.mkdir(exist_ok=True)
random.seed(17)
# Synthetic dialect phrases for seven review themes.
P={
'login_issue':{'Saudi':'ما اقدر اسجل دخول','Egyptian':'مش عارف اسجل دخول','Moroccan':'ما قادرش ندخل للحساب','Gulf':'مو قادر ادخل حسابي','Iraqi':'ما اكدر اسجل دخول','English':"can't log into my account",'Arabizi':'ma agdar asajel d5ool'},
'crash':{'Saudi':'التطبيق يقفل فجأة','Egyptian':'الابلكيشن بيقفل لوحده','Moroccan':'التطبيق كيخرج بوحدو','Gulf':'التطبيق يفصل فجأة','Iraqi':'التطبيق يسد فجأة','English':'the app crashes suddenly','Arabizi':'el app yegfel faga2a'},
'performance':{'Saudi':'التطبيق بطيء ويتأخر','Egyptian':'الابلكيشن بطيء اوي','Moroccan':'التطبيق بطيء بزاف','Gulf':'التطبيق بطيء وايد','Iraqi':'التطبيق بطيء كلش','English':'the app is very slow','Arabizi':'el app batee2 awy'},
'payment':{'Saudi':'انخصم المبلغ مرتين','Egyptian':'اتخصم المبلغ مرتين','Moroccan':'تخصم ليا المبلغ جوج مرات','Gulf':'انسحب المبلغ مرتين','Iraqi':'خصموا المبلغ مرتين','English':'I was charged twice','Arabizi':'enkhasam el mablagh marteen'},
'usability':{'Saudi':'القوائم مو واضحة','Egyptian':'القوايم مش واضحة','Moroccan':'القوائم ما واضحاش','Gulf':'القوائم مب واضحة','Iraqi':'القوائم مو واضحة','English':'the menus are confusing','Arabizi':'el gawayeem mesh wad7a'},
'feature_request':{'Saudi':'ياليت تضيفون الوضع الداكن','Egyptian':'يا ريت تضيفوا الوضع الداكن','Moroccan':'بغيت تزيدو الوضع الليلي','Gulf':'أبيكم تضيفون الوضع الداكن','Iraqi':'اريد تضيفون الوضع الداكن','English':'please add dark mode','Arabizi':'ya reit tedefo dark mode'},
'positive_experience':{'Saudi':'التطبيق ممتاز وسهل','Egyptian':'الابلكيشن جميل وسهل','Moroccan':'التطبيق زوين وساهل','Gulf':'التطبيق ممتاز وسهل الاستخدام','Iraqi':'التطبيق حلو وسهل','English':'the app is excellent and easy','Arabizi':'el app momtaz w sahl'}}
ALT={
'login_issue':{'Saudi':'كلمة المرور ما تدخلني لحسابي','Egyptian':'كلمة السر مش راضية تدخلني','Moroccan':'كلمة السر ما دخلاش للحساب','Gulf':'كلمة السر ما تدخلني للحساب','Iraqi':'كلمة السر ما تدخلني للحساب','English':'my password will not let me into the account','Arabizi':'kelmet el ser mesh radya ted5elny'},
'crash':{'Saudi':'الشاشة تسود ويطلعني','Egyptian':'الشاشة بتسود ويخرجني','Moroccan':'الشاشة كتولي كحلة وكيخرجني','Gulf':'يهنق ويطلعني من البرنامج','Iraqi':'تسود الشاشة ويسد البرنامج','English':'the screen goes black then closes','Arabizi':'el screen teswed w yegfel'},
'performance':{'Saudi':'التحميل ياخذ وقت طويل','Egyptian':'التحميل بياخد وقت طويل','Moroccan':'التحميل كياخذ وقت بزاف','Gulf':'التحميل ياخذ وقت وايد','Iraqi':'التحميل ياخذ وقت كلش','English':'loading takes a very long time','Arabizi':'el loading yekhod wa2t taweel'},
'payment':{'Saudi':'طلع علي خصم اضافي','Egyptian':'اتخصم مني مبلغ زيادة','Moroccan':'تخصم مني مبلغ زايد','Gulf':'طلع لي خصم زيادة','Iraqi':'انسحب مني مبلغ زايد','English':'there is an extra charge on my bill','Arabizi':'t5asam menni mablagh zeyada'},
'usability':{'Saudi':'ما لقيت صفحة الاعدادات','Egyptian':'مش لاقي صفحة الاعدادات','Moroccan':'ما لقيتش صفحة الاعدادات','Gulf':'ما حصلت صفحة الاعدادات','Iraqi':'ما لكيت صفحة الاعدادات','English':'I cannot find the settings page','Arabizi':'ma la2eit saf7et el e3dadat'},
'feature_request':{'Saudi':'اضيفوا خيار تسجيل بالبصمة','Egyptian':'ضيفوا تسجيل بالبصمة','Moroccan':'زيدو خاصية الدخول بالبصمة','Gulf':'ضيفوا خاصية البصمة','Iraqi':'ضيفوا تسجيل دخول بالبصمة','English':'please add fingerprint sign in','Arabizi':'3afo fingerprint login option'},
'positive_experience':{'Saudi':'تجربتي معه حلوة وسريعة','Egyptian':'تجربتي معاه حلوة وسريعة','Moroccan':'التجربة ديالي زوينة وسريعة','Gulf':'تجربتي وياه ممتازة وسريعة','Iraqi':'تجربتي وياه كلش حلوة','English':'my experience has been smooth and positive','Arabizi':'tajribti ma3ah 7elwa w saree3a'}}
D={'Saudi':('Arabic','Saudi Arabic'),'Egyptian':('Arabic','Egyptian Arabic'),'Moroccan':('Arabic','Moroccan Darija'),'Gulf':('Arabic','Gulf Arabic'),'Iraqi':('Arabic','Iraqi Arabic'),'English':('English','Standard English'),'Arabizi':('Arabizi','Arabizi')}
PRE={'Saudi':['يا جماعة، ','والله ','للأسف ','من امس و','كل ما افتح التطبيق '],'Egyptian':['يا جماعة، ','بصراحة ','للأسف ','من امبارح و','كل ما افتح الابلكيشن '],'Moroccan':['عفاكم، ','بصراحة ','للأسف ','من البارح و','كل مرة كنفتح التطبيق '],'Gulf':['يا جماعة، ','والله ','للأسف ','من امس و','كل ما افتح التطبيق '],'Iraqi':['شباب، ','والله ','للأسف ','من البارحة و','كل ما افتح التطبيق '],'English':['Honestly, ','Unfortunately, ','Since yesterday, ','Whenever I open the app, ','Please note: '],'Arabizi':['ya jama3a, ','wallah ','l2asaf ','men embare7 w','kol ma afta7 el app ']}
SUF={'Saudi':['',' من فضلكم',' وما ضبط معي',' مرة'],'Egyptian':['',' لو سمحتوا',' ومش راضي يشتغل',' خالص'],'Moroccan':['',' عافاكم',' وما خدامش',' بزاف'],'Gulf':['',' لو سمحتوا',' وما يضبط',' وايد'],'Iraqi':['',' اذا ممكن',' وما يشتغل',' كلش'],'English':['',' please',' and it still does not work',' lately'],'Arabizi':['',' please',' w ma zabat',' lately']}
rows=[]
for c,phrases in P.items():
 for dialect,phrase in phrases.items():
  lang,dn=D[dialect]
  for phrase_id,phrase in enumerate([phrase,ALT[c][dialect]]):
   for pi,prefix in enumerate(PRE[dialect]):
    for si,suffix in enumerate(SUF[dialect]):
     fid=pi*4+si
     rows.append({'review':prefix+phrase+suffix,'category':c,'sentiment':'neutral' if c=='feature_request' else ('positive' if c=='positive_experience' else 'negative'),'language':lang,'dialect':dn,'template_id':fid,'split':'test' if phrase_id==1 else 'train'})
# Baseline multinomial Naive Bayes over word unigrams and bigrams.
def toks(s): return re.findall(r'[a-z0-9]+|[ء-ي]+',s.lower())
def feats(s,mode):
 t=toks(s)
 if mode=='word': return Counter(t+[' '.join(t[i:i+2]) for i in range(len(t)-1)])
 out=Counter()
 for w in t:
  w='<'+w+'>'
  for n in (2,3,4): out.update(w[i:i+n] for i in range(len(w)-n+1))
 return out
class NB:
 def __init__(self,mode): self.mode=mode
 def fit(self,data):
  self.classes=sorted({r['category'] for r in data}); self.fc={c:Counter() for c in self.classes}; self.total=Counter(); self.pr={c:math.log(sum(r['category']==c for r in data)/len(data)) for c in self.classes}
  for r in data:
   f=feats(r['review'],self.mode); self.fc[r['category']].update(f); self.total[r['category']]+=sum(f.values())
  self.v=set().union(*(set(x) for x in self.fc.values())); self.vsize=len(self.v)
  self.lp={c:{w:math.log((self.fc[c][w]+.5)/(self.total[c]+.5*self.vsize)) for w in self.v} for c in self.classes}; return self
 def pred(self,s):
  f=feats(s,self.mode); return max(self.classes,key=lambda c:self.pr[c]+sum(n*self.lp[c].get(w,math.log(.5/(self.total[c]+.5*self.vsize))) for w,n in f.items()))
def metrics(data,pred):
 y=[r['category'] for r in data]; classes=sorted(P); f=[]
 for c in classes:
  tp=sum(a==c and b==c for a,b in zip(y,pred)); fp=sum(a!=c and b==c for a,b in zip(y,pred)); fn=sum(a==c and b!=c for a,b in zip(y,pred)); p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0; f.append(2*p*r/(p+r) if p+r else 0)
 return {'accuracy':sum(a==b for a,b in zip(y,pred))/len(y),'macro_f1':sum(f)/len(f)}
train=[r for r in rows if r['split']=='train']; test=[r for r in rows if r['split']=='test']; results={}; preds={}
for mode in ('word','char'):
 m=NB(mode).fit(train); preds[mode]=[m.pred(r['review']) for r in test]; results[mode]=metrics(test,preds[mode])
best=max(results,key=lambda m:results[m]['macro_f1']); slices={}
for d in sorted({r['dialect'] for r in test}):
 ix=[i for i,r in enumerate(test) if r['dialect']==d]; slices[d]=metrics([test[i] for i in ix],[preds[best][i] for i in ix])
with (ROOT/'data'/'sample_reviews.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
report={'total':len(rows),'train':len(train),'test':len(test),'classes':len(P),'dialects':len(D),'class_counts':dict(Counter(r['category'] for r in rows)),'dialect_counts':dict(Counter(r['dialect'] for r in rows)),'results':results,'best':best,'by_dialect':slices}
# Cross-dialect stress test: exclude one dialect entirely from training.
loo={}
for mode in ('word','char'):
 loo[mode]={}
 for dialect in sorted({r['dialect'] for r in rows}):
  tr=[r for r in rows if r['dialect']!=dialect]
  te=[r for r in rows if r['dialect']==dialect]
  model=NB(mode).fit(tr); pred=[model.pred(r['review']) for r in te]
  loo[mode][dialect]=metrics(te,pred)
report['leave_one_dialect_out']=loo
with (OUT/'test_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f); w.writerow(['review','dialect','actual','predicted'])
 for r,pred in zip(test,preds[best]): w.writerow([r['review'],r['dialect'],r['category'],pred])
(ROOT/'reports'/'experiment_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
