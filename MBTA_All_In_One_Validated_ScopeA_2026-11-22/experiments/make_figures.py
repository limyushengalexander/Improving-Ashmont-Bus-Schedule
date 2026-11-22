"""Generate separate evidence figures with Matplotlib's default color cycle."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1];figures=root/'figures';figures.mkdir(exist_ok=True)
summary=pd.read_csv(root/'results/experiment_summary.csv')
comparison=pd.read_csv(root/'results/nominal_method_comparison.csv')
fig,ax=plt.subplots(figsize=(8,4.6))
bars=ax.bar(['Existing timetable','Simple heuristic','MILP optimum'],comparison.mean_wait_min)
ax.bar_label(bars,labels=[f'{v:.2f}' for v in comparison.mean_wait_min],padding=4)
ax.set_ylim(0,16);ax.set_ylabel('Mean waiting after transfer allowance (minutes)');ax.set_title('The simple heuristic matches the Scope A optimum')
fig.text(.02,.01,'41 equally weighted scheduled transfer opportunities; assumed 3-minute allowance.',fontsize=9)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figures/'01_method_comparison.png',dpi=180,bbox_inches='tight');plt.close(fig)
cases=summary[summary.case.isin(['joint_t120_r180_b120','nominal','joint_t300_r180_b120'])].sort_values('transfer_seconds')
fig,ax=plt.subplots(figsize=(8,4.8));allowance=cases.transfer_seconds/60
for column,label,marker in [('baseline_mean_wait_min','Existing timetable','o'),('optimized_mean_wait_min','Reoptimized for each allowance','s'),('frozen_nominal_mean_wait_min','Unchanged 3-minute-optimal timetable','^')]:
 ax.plot(allowance,cases[column],marker=marker,label=label)
ax.set_xticks([2,3,5]);ax.set_xlabel('Assumed passenger transfer allowance (minutes)');ax.set_ylabel('Mean waiting after allowance (minutes)');ax.set_ylim(0,18);ax.set_title('The recommended shifts depend on the transfer allowance');ax.legend(loc='lower left')
fig.text(.02,.01,'Same 41 opportunities. Total transfer time adds the allowance; this is not a delay forecast.',fontsize=9)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figures/'02_transfer_allowance_stress_test.png',dpi=180,bbox_inches='tight');plt.close(fig)
cases=summary[summary.case.isin(['headway_tolerance_0','headway_tolerance_120','nominal','headway_tolerance_600'])].sort_values('headway_deviation_seconds')
fig,ax=plt.subplots(figsize=(8,4.6));x=cases.headway_deviation_seconds/60;ax.plot(x,cases.optimized_mean_wait_min,marker='o')
for xv,yv in zip(x,cases.optimized_mean_wait_min):ax.annotate(f'{yv:.2f}',(xv,yv),xytext=(0,7),textcoords='offset points',ha='center')
ax.set_xticks([0,2,5,10]);ax.set_ylim(0,15);ax.set_xlabel('Permitted change in each original headway (± minutes)');ax.set_ylabel('Reoptimized mean waiting (minutes)');ax.set_title('Transfer coordination versus departure-spacing limits')
fig.text(.02,.01,'Values are study design choices, not verified MBTA service-spacing requirements.',fontsize=9)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figures/'03_headway_sensitivity.png',dpi=180,bbox_inches='tight');plt.close(fig)
changes=pd.read_csv(root/'results/individual_transfer_changes.csv');changes['arrival_min']=changes.arrival_time.map(lambda t:int(t.split(':')[0])*60+int(t.split(':')[1]))
fig,ax=plt.subplots(figsize=(9,4.8))
for route,marker in [(22,'o'),(23,'^')]:
 part=changes[changes.route_id==route];ax.scatter(part.arrival_min,part.saved_sec/60,marker=marker,label=f'Route {route}')
ax.axhline(0,linestyle='--',linewidth=1);ax.set_xticks([960,990,1020,1050,1080,1110,1140],['16:00','16:30','17:00','17:30','18:00','18:30','19:00'])
ax.set_xlabel('Scheduled arrival at Ashmont');ax.set_ylabel('Waiting reduction (minutes; negative = worse)');ax.set_title('18 opportunities improve, 7 worsen, 16 remain unchanged');ax.legend()
fig.text(.02,.01,'Largest improvement: 30 minutes. All seven worsened opportunities incur two additional minutes.',fontsize=9)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(figures/'04_individual_transfer_changes.png',dpi=180,bbox_inches='tight');plt.close(fig)
print('Saved four figures in',figures)
