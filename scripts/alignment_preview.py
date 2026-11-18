"""Offline batch listening review; no application or server dependency."""
import json
from pathlib import Path

from audio_alignment import write_json


def build_preview(root: Path) -> dict:
    samples=[]
    for path in sorted(root.rglob('timeline.json')):
        directory=path.parent
        if not (directory/'sample.json').is_file() or not (directory/'quality.json').is_file():
            continue
        sample=json.loads((directory/'sample.json').read_text())
        quality=json.loads((directory/'quality.json').read_text())
        timeline=json.loads(path.read_text())
        if quality.get('alignmentKey') != sample.get('alignmentKey') or (directory/'failure.json').exists():
            continue
        from audio_alignment import sha256_file, validate_timeline
        if quality.get('timelineSha256') != sha256_file(path):
            continue
        validate_timeline(timeline,sample['content'],sample['audioSha256'])
        samples.append({'sample':sample,'timeline':json.loads(path.read_text()),
                        'quality':quality,
                        'audio':str(directory.relative_to(root)/'sample.mp3')})
    if not samples:
        raise ValueError('No successful local alignments to preview')
    totals={'sampleCount':len(samples),'durationSeconds':round(sum(s['quality']['durationMs'] for s in samples)/1000,3),
            'tokenCount':sum(s['quality']['tokenCount'] for s in samples),
            'timedTokenCount':sum(s['quality']['timedTokenCount'] for s in samples),
            'alignmentSeconds':round(sum(s['quality']['alignmentSeconds'] for s in samples),3),
            'lowScoreTokenCount':sum(len(s['quality']['lowScoreTokens']) for s in samples),
            'humanSyncReview':'not_performed','uploaded':False,'attached':False}
    write_json(root/'batch-metrics.json',totals)
    html=r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline';script-src 'unsafe-inline';media-src 'self' file: data:;img-src 'self' data:">
<title>WhisperX · 九段新闻对齐验证</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#263328;background:#f6f5ef}*{box-sizing:border-box}body{margin:0}main{max-width:1180px;margin:auto;padding:36px 30px 80px}.eyebrow{font-size:12px;letter-spacing:.12em;color:#5c7059}h1{font-weight:500;font-size:32px;margin:13px 0}h2{font-family:Georgia,serif;font-size:27px;font-weight:500;line-height:1.25}p{font-size:14px;color:#61705e;line-height:1.7}.stats{display:flex;gap:30px;flex-wrap:wrap;border-block:1px solid #d6dccc;padding:16px 0;margin:23px 0}.stats b{font-size:23px;display:block}.stats small{font-size:12px;color:#697765}.workspace{display:grid;grid-template-columns:245px minmax(0,1fr);gap:30px}.sidebar button{display:block;width:100%;text-align:left;margin-bottom:8px;font:inherit;font-size:13px;line-height:1.5;padding:11px 13px;border:1px solid #dce1d4;border-radius:7px;background:#fbfcf7;cursor:pointer}.sidebar button.selected{background:#e4eddf;border-color:#8b9e83}.sidebar small{display:block;color:#6a7864;font-size:11px;margin-top:5px}.player{position:sticky;top:10px;background:#fffefa;border:1px solid #dce0d4;padding:15px 17px;border-radius:10px;z-index:2}audio{width:100%;height:40px}.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:8px}button,select{font:inherit;font-size:13px;padding:6px 10px;border:1px solid #cdd8c8;border-radius:5px;background:#fff;cursor:pointer}.current{font-size:12px;font-variant-numeric:tabular-nums;min-height:19px;margin-top:10px}.reading{font-family:Georgia,serif;font-size:21px;line-height:1.85;white-space:pre-wrap;margin:24px 0}.word{border-radius:3px;cursor:pointer}.word.active{background:#ffe28c;box-shadow:0 0 0 2px #ffe28c}.word.low{border-bottom:1px dotted #ae6c26}.word.missing{border-bottom:2px dashed #af4637}.risk button{margin:4px 4px 4px 0;font-family:Georgia,serif}.note{background:#ebefe4;border-radius:7px;padding:12px 15px;font-size:12px;line-height:1.75}.review{margin-top:25px;padding-top:20px;border-top:1px solid #d6dccc}textarea{display:block;width:100%;height:70px;font:inherit;font-size:13px;border:1px solid #ccd6c6;border-radius:5px;padding:9px;margin:10px 0}table{border-collapse:collapse;font-size:12px;width:100%;margin:10px 0}th,td{text-align:left;border-bottom:1px solid #e0e5da;padding:7px}summary{font-size:13px;cursor:pointer}.quality{font-size:12px;color:#6b795f}.review select{margin-left:8px}@media(max-width:760px){main{padding:25px 17px}.workspace{grid-template-columns:1fr}.sidebar{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.sidebar button{font-size:11px;margin:0;padding:8px}.stats{gap:18px}h1{font-size:27px}.reading{font-size:20px}}
</style><main><div class="eyebrow">LEVEL READ · WHISPERX · LOCAL VALIDATION</div><h1>三篇新闻，九段原声对齐</h1><p>本地 CPU 实验 · 不修改原新闻存档 · 不调用 TTS、上传或数据库</p><div id="stats" class="stats"></div><div class="workspace"><nav id="samples" class="sidebar" aria-label="音频样本"></nav><section><h2 id="title"></h2><p id="quality" class="quality"></p><div class="player"><audio id="audio" controls preload="metadata"></audio><div class="controls"><button id="restart">从头播放</button><button id="middle">跳至中段</button><label>速度 <select id="rate"><option value="0.7">0.7×</option><option value="1" selected>1×</option><option value="1.5">1.5×</option></select></label></div><div id="current" class="current" aria-live="off"></div></div><article id="text" class="reading" lang="en"></article><div class="note">黄色：当前词；点线：模型低分；红色虚线：未对齐。覆盖率不等于同步准确率。所有样本初始状态均为待人工听辨；数字、缩写及专名需重点检查。点击正文单词或下方风险词可跳播。</div><h3 style="font-size:14px">风险词（含数字与低分项）</h3><div id="risk" class="risk"></div><details><summary>逐词时间与模型分数</summary><table><thead><tr><th>词</th><th>开始/秒</th><th>结束/秒</th><th>分数</th></tr></thead><tbody id="rows"></tbody></table></details><div class="review"><label>听辨结论<select id="verdict"><option value="pending">未听辨</option><option value="usable">已听辨：同步可用</option><option value="needs_fix">已听辨：需修复</option></select></label><textarea id="notes" placeholder="记录问题词、时间与现象；不能仅凭覆盖率批准"></textarea><button id="export">下载听辨记录 JSON</button><p>记录绑定当前时间轴和音频 hash。手动结论不会上传，也不会自动批准生产或写入新闻包。</p></div></section></div></main>
<script>
const SAMPLES=__SAMPLES__,TOTALS=__TOTALS__;
const $=id=>document.getElementById(id),audio=$('audio'),reviews={};let selected=-1,active=[],frame=null,map=new Map(),pendingSeek=null;
for(const [v,l]of [[TOTALS.sampleCount,'段音频'],[(TOTALS.durationSeconds/60).toFixed(2)+' min','原声总时长'],[TOTALS.timedTokenCount+'/'+TOTALS.tokenCount,'有时间的词'],[TOTALS.alignmentSeconds.toFixed(2)+'s','CPU 对齐总计算'],[TOTALS.lowScoreTokenCount,'低模型分数词']]){const d=document.createElement('div'),b=document.createElement('b'),s=document.createElement('small');b.textContent=v;s.textContent=l;d.append(b,s);$('stats').append(d)}
SAMPLES.forEach((s,i)=>{const b=document.createElement('button');b.dataset.sample=i;const label=document.createElement('span'),info=document.createElement('small');label.textContent=s.sample.newsTitle;info.textContent=`Level ${s.sample.level} · ${(s.quality.durationMs/1000).toFixed(1)}s · 低分 ${s.quality.lowScoreTokens.length}`;b.append(label,info);b.onclick=()=>choose(i);$('samples').append(b)});
function save(){if(selected>=0)reviews[selected]={verdict:$('verdict').value,notes:$('notes').value}}
function choose(i){save();audio.pause();cancelAnimationFrame(frame);selected=i;active=[];map=new Map();pendingSeek=null;$('restart').disabled=true;$('middle').disabled=true;const s=SAMPLES[i];$('title').textContent=s.sample.newsTitle+' · Level '+s.sample.level;$('quality').textContent=`${s.quality.coveragePercent}% 时间覆盖 · ${s.quality.tokenCount} 词 · ${s.quality.alignmentSeconds}s 计算 · 不插值 · 待听辨`;
document.querySelectorAll('[data-sample]').forEach(b=>b.classList.toggle('selected',Number(b.dataset.sample)===i));audio.src=s.audio;audio.playbackRate=Number($('rate').value);$('text').replaceChildren();$('risk').replaceChildren();$('rows').replaceChildren();let cursor=0;
const diag=new Map(s.quality.wordDiagnostics.map(d=>[d.tokenId,d]));for(const t of s.timeline.tokens){$('text').append(document.createTextNode(s.sample.content.slice(cursor,t.startChar)));const el=document.createElement('span'),d=diag.get(t.id);el.className='word'+(d.unaligned?' missing':d.score===null||d.score<.5?' low':'');el.textContent=s.sample.content.slice(t.startChar,t.endChar);el.dataset.token=t.id;el.title=d.startMs===undefined?'未对齐':`${d.startMs/1000}–${d.endMs/1000}s · ${d.score}`;if(d.startMs!==undefined)el.onclick=()=>jump(d.startMs);map.set(t.id,el);$('text').append(el);cursor=t.endChar;
if(d.risk){const b=document.createElement('button');b.textContent=d.text;b.title=el.title;b.disabled=d.startMs===undefined;b.onclick=()=>jump(d.startMs);$('risk').append(b)}const tr=document.createElement('tr');for(const val of[d.text,d.startMs===undefined?'—':(d.startMs/1000).toFixed(3),d.endMs===undefined?'—':(d.endMs/1000).toFixed(3),d.score??'—']){const td=document.createElement('td');td.textContent=val;tr.append(td)}$('rows').append(tr)}$('text').append(document.createTextNode(s.sample.content.slice(cursor)));$('verdict').value=reviews[i]?.verdict??'pending';$('notes').value=reviews[i]?.notes??'';update()}
function seek(seconds,play){if(audio.readyState<1){pendingSeek={seconds,play,sample:selected};return}audio.currentTime=seconds;if(play)audio.play().catch(e=>$('current').textContent=e.message);update()}
function jump(ms){seek(Math.max(0,ms/1000-.25),true)}
function update(){if(selected<0)return;const cues=SAMPLES[selected].timeline.cues,ms=audio.currentTime*1000;let lo=0,hi=cues.length-1,k=-1;while(lo<=hi){const mid=(lo+hi)>>1;if(cues[mid].startMs<=ms){k=mid;lo=mid+1}else hi=mid-1}const ids=!audio.ended&&k>=0&&ms<cues[k].endMs?cues[k].tokenIds:[];if(ids.join(',')!==active.join(',')){active.forEach(id=>map.get(id)?.classList.remove('active'));ids.forEach(id=>map.get(id)?.classList.add('active'));active=ids}$('current').textContent=`${audio.currentTime.toFixed(2)} / ${(SAMPLES[selected].quality.durationMs/1000).toFixed(2)} 秒 · ${ids.map(id=>map.get(id).textContent).join(' ')||'停顿/未对齐区间'}`}
function tick(){update();if(!audio.paused&&!audio.ended)frame=requestAnimationFrame(tick)}audio.onplay=()=>{cancelAnimationFrame(frame);tick()};audio.onpause=()=>{cancelAnimationFrame(frame);update()};['timeupdate','seeking','seeked','ended'].forEach(e=>audio.addEventListener(e,update));audio.onloadedmetadata=()=>{$('restart').disabled=false;$('middle').disabled=false;audio.playbackRate=Number($('rate').value);if(pendingSeek&&pendingSeek.sample===selected){const p=pendingSeek;pendingSeek=null;seek(p.seconds,p.play)}update()};audio.onerror=()=>$('current').textContent='音频无法加载，请保持解压后的文件夹结构';$('restart').onclick=()=>seek(0,true);$('middle').onclick=()=>seek(SAMPLES[selected].quality.durationMs/2000,false);$('rate').onchange=e=>audio.playbackRate=Number(e.target.value);$('verdict').onchange=save;$('notes').oninput=save;
$('export').onclick=()=>{save();const record={schemaVersion:1,createdAt:new Date().toISOString(),scope:'manual_listening_review_only',samples:SAMPLES.map((s,i)=>({titleid:s.sample.titleid,level:s.sample.level,contentSha256:s.timeline.contentSha256,audioSha256:s.timeline.audioSha256,timelineSha256:s.quality.timelineSha256,...(reviews[i]??{verdict:'pending',notes:''})}))};const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='alignment-listening-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
choose(0);
</script></html>'''
    html=html.replace('__SAMPLES__',json.dumps(samples,ensure_ascii=False).replace('<','\\u003c')).replace('__TOTALS__',json.dumps(totals))
    (root/'index.html').write_text(html,encoding='utf-8')
    return totals
