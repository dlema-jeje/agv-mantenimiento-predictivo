#!/usr/bin/env python3
"""Adelanto neuronal CWRU: partición temporal antes de ventanas, 6 características, MLP."""
import argparse, csv, json, re, sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.io import loadmat
from scipy.stats import kurtosis, skew
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

N=2048; STEP=1024; SPLITS=('entrenamiento','validacion','prueba')
FEATURES=['rms','pico','curtosis','asimetria','desviacion_estandar','factor_cresta']

def guess_label(path, root):
    # Solo etiquetas inequívocas de directorio/nombre, nunca asignar por defecto.
    parts=[p.lower() for p in path.relative_to(root).parts]
    for s in reversed(parts):
        tokens=re.split(r'[^a-z0-9]+',s)
        if any(t in ('normal','healthy','sano') for t in tokens): return 'normal'
        if any(t in ('inner','ir','innerace') for t in tokens): return 'inner_race'
        if any(t in ('outer','or','outerrace') for t in tokens): return 'outer_race'
        if any(t in ('ball','bola','rolling') for t in tokens): return 'ball'
    return None

def read_signal(path, column=None):
    if path.suffix.lower()=='.mat':
        m=loadmat(path)
        candidates=[]
        for k,v in m.items():
            if k.startswith('__') or not isinstance(v,np.ndarray) or not np.issubdtype(v.dtype,np.number): continue
            if v.size<3*N: continue
            if v.ndim>2 or (v.ndim==2 and min(v.shape)!=1): continue
            score=2 if re.search(r'_DE_time$',k,re.I) else (1 if re.search(r'_FE_time$',k,re.I) else 0)
            candidates.append((score,k,np.asarray(v,dtype=float).ravel()))
        if not candidates: raise ValueError('No hay vector de señal válido (>=6144 muestras)')
        candidates.sort(key=lambda z:(-z[0],z[1]))
        if len(candidates)>1 and candidates[0][0]==candidates[1][0]:
            raise ValueError('Varios vectores ambiguos: '+','.join(x[1] for x in candidates[:5]))
        return candidates[0][2],candidates[0][1]
    if path.suffix.lower()=='.csv':
        import pandas as pd
        df=pd.read_csv(path)
        if column:
            if column not in df: raise ValueError('Columna inexistente: '+column)
            return pd.to_numeric(df[column],errors='coerce').to_numpy(float),column
        cols=[c for c in df if pd.api.types.is_numeric_dtype(df[c]) and c.lower() not in ('time','tiempo','timestamp','index','sample','muestra','label','clase','fs')]
        if len(cols)!=1: raise ValueError('CSV requiere una columna numérica inequívoca; use --columna')
        return df[cols[0]].to_numpy(float),cols[0]
    raise ValueError('Formato no admitido')

def feats(w):
    w=np.asarray(w,float)
    rms=float(np.sqrt(np.mean(w*w))); peak=float(np.max(np.abs(w)))
    return [rms,peak,float(kurtosis(w,fisher=True,bias=False)),float(skew(w,bias=False)),float(np.std(w)),float(peak/rms if rms>1e-12 else 0)]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--datos',required=True,help='Directorio de señales crudas .mat/.csv')
    ap.add_argument('--salida',default='entrega_avance2/evidencias/neuronal_cwru')
    ap.add_argument('--columna',help='Nombre de columna de señal en archivos CSV')
    ap.add_argument('--manifest',help='CSV con columnas archivo,clase; rutas relativas a --datos')
    args=ap.parse_args(); root=Path(args.datos).expanduser().resolve(); out=Path(args.salida).resolve()
    if not root.is_dir(): sys.exit('ERROR: No existe directorio de señales: '+str(root))
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.mat','.csv'))
    if not files: sys.exit('ERROR: No se encontraron señales .mat/.csv en '+str(root))
    mapping={}
    if args.manifest:
        with open(args.manifest,newline='',encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                mapping[str(Path(row['archivo']))]=row['clase'].strip()
    rows=[]; summary=[]; errors=[]; classes=Counter()
    for p in files:
        rel=str(p.relative_to(root)); label=mapping.get(rel) if args.manifest else guess_label(p,root)
        if not label:
            errors.append(f'{rel}: etiqueta desconocida (use carpetas normal/inner/outer/ball o --manifest)');continue
        try:
            x,channel=read_signal(p,args.columna)
            if not np.all(np.isfinite(x)): raise ValueError('Señal contiene NaN o Inf')
            n=len(x); b1=int(n*.70); b2=int(n*.85)
            if min(b1,b2-b1,n-b2)<N: raise ValueError(f'Registro corto para dividir 70/15/15: {n} muestras')
            counts={}
            for split,a,b in zip(SPLITS,(0,b1,b2),(b1,b2,n)):
                count=0
                for start in range(a,b-N+1,STEP):
                    vals=feats(x[start:start+N]);
                    if not np.all(np.isfinite(vals)): raise ValueError('Características no finitas')
                    rows.append({'archivo':rel,'canal':channel,'clase':label,'conjunto':split,'inicio_muestra':start,'fin_muestra_exclusivo':start+N,**dict(zip(FEATURES,vals))})
                    count+=1
                counts[split]=count
            classes[label]+=1
            summary.append({'archivo':rel,'clase':label,'muestras':n,'corte_70':b1,'corte_85':b2,**counts})
        except Exception as e: errors.append(f'{rel}: {e}')
    if errors:
        print('ERRORES / ARCHIVOS NO UTILIZADOS:')
        for e in errors[:60]: print(' -',e)
        sys.exit('Se detuvo para evitar resultados incompletos o etiquetas incorrectas. Corrija archivos o manifiesto.')
    if len(classes)<2: sys.exit('ERROR: Se requieren al menos dos clases diferentes.')
    if any(sum(r['conjunto']==s for r in rows)==0 for s in SPLITS): sys.exit('ERROR: Falta algún conjunto.')
    out.mkdir(parents=True,exist_ok=True)
    def write_csv(path,data):
        with open(path,'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    write_csv(out/'caracteristicas_ventanas.csv',rows)
    write_csv(out/'particiones_por_registro.csv',summary)
    X={s:np.array([[r[k] for k in FEATURES] for r in rows if r['conjunto']==s]) for s in SPLITS}
    y={s:np.array([r['clase'] for r in rows if r['conjunto']==s]) for s in SPLITS}
    scaler=StandardScaler().fit(X['entrenamiento'])
    Z={s:scaler.transform(X[s]) for s in SPLITS}
    joblib.dump(scaler,out/'standard_scaler_train.joblib')
    model=MLPClassifier(hidden_layer_sizes=(32,16),activation='relu',max_iter=500,early_stopping=False,random_state=42)
    model.fit(Z['entrenamiento'],y['entrenamiento'])
    joblib.dump(model,out/'mlp_primer_entrenamiento.joblib')
    labels=sorted(classes)
    scores={s:float(accuracy_score(y[s],model.predict(Z[s]))) for s in SPLITS}
    pred=model.predict(Z['prueba'])
    report=classification_report(y['prueba'],pred,labels=labels,zero_division=0)
    cm=confusion_matrix(y['prueba'],pred,labels=labels)
    fig,ax=plt.subplots(figsize=(7,5));im=ax.imshow(cm,cmap='Blues')
    ax.set_xticks(range(len(labels)),labels,rotation=30,ha='right');ax.set_yticks(range(len(labels)),labels)
    ax.set_xlabel('Predicción');ax.set_ylabel('Clase real');ax.set_title('Matriz de confusión — prueba')
    for i in range(len(labels)):
        for j in range(len(labels)):ax.text(j,i,str(cm[i,j]),ha='center',va='center')
    fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(out/'matriz_confusion_prueba.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));ax.plot(model.loss_curve_);ax.set(xlabel='Iteración',ylabel='Pérdida',title='Primer entrenamiento MLP');fig.tight_layout();fig.savefig(out/'curva_entrenamiento.png',dpi=160);plt.close(fig)
    # Auditoría formal de intervalos: cada ventana está completamente dentro de su tramo.
    for r in rows:
        sm=next(z for z in summary if z['archivo']==r['archivo'])
        a,b={'entrenamiento':(0,sm['corte_70']),'validacion':(sm['corte_70'],sm['corte_85']),'prueba':(sm['corte_85'],sm['muestras'])}[r['conjunto']]
        assert a<=r['inicio_muestra'] and r['fin_muestra_exclusivo']<=b
    audit={'particion_antes_de_ventanas':True,'ventana_muestras':N,'solapamiento_muestras':N-STEP,'solapamiento_porcentaje':50,'sin_muestras_compartidas_entre_conjuntos':True,'registros_por_clase':dict(classes),'ventanas_por_conjunto':{s:len(y[s]) for s in SPLITS},'exactitud':scores,'nota':'Partición temporal dentro de cada registro; ventanas de un mismo registro pueden compartir características de origen entre conjuntos, aunque no muestras.'}
    (out/'auditoria_particiones.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    text=['ADELANTO NEURONAL CWRU — EVIDENCIA REAL','',f'Registros procesados: {len(summary)}','Clases: '+str(dict(classes)),'1. Cada registro se dividió temporalmente 70/15/15 antes de segmentar.','2. Ventanas de 2048 muestras, paso 1024 (50 % solapamiento).','3. Características: '+', '.join(FEATURES),'4. CSV con conjunto, clase, archivo e índices de muestra.','5. StandardScaler ajustado exclusivamente con entrenamiento.','6. Primer entrenamiento MLP(32,16) ejecutado.','','Ventanas: '+str(audit['ventanas_por_conjunto']),'Exactitud (train/val/test): '+str(scores),'','REPORTE DE CLASIFICACIÓN — PRUEBA',report,'ADVERTENCIA: el corte temporal evita compartir muestras, pero no equivale a evaluar sobre máquinas o registros independientes.']
    (out/'avance_neuronal_cwru.txt').write_text('\n'.join(text),encoding='utf-8')
    print('\n'.join(text));print('\nEVIDENCIAS GUARDADAS EN:',out)
if __name__=='__main__':main()
