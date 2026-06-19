"""Static HTML/JS for the MemPalace browser UI."""

GRAPH_HTML = """\n<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MemPalace</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/standalone/umd/vis-network.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/15.0.7/marked.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/styles/vis-network.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#1a1a2e;color:#e0e0e0;overflow:hidden}
#graph{position:absolute;top:0;left:280px;right:0;bottom:0;transition:bottom .25s}
#graph.alone{left:0}
#graph.info-open{bottom:50vh}
#sidebar{position:fixed;left:0;top:0;bottom:0;width:280px;background:rgba(22,22,42,0.98);border-right:1px solid #333;z-index:50;display:flex;flex-direction:column;transition:transform .2s}
#sidebar.hidden{transform:translateX(-100%)}
#sidebar-toggle{position:fixed;left:8px;top:8px;z-index:60;background:rgba(26,26,46,0.92);border:1px solid #444;border-radius:6px;color:#ccc;padding:4px 10px;cursor:pointer;font-size:16px}
#sidebar-toggle:hover{background:rgba(100,255,218,0.1);color:#64ffda}
#tree-header{padding:12px 14px 12px 48px;border-bottom:1px solid #333;display:flex;align-items:center;gap:8px}
#tree-header h2{font-size:14px;font-weight:600;color:#64ffda;margin:0}
#tree-stats{color:#666;font-size:11px;margin-left:auto}
#tree-search{padding:8px 14px;border-bottom:1px solid #222}
#tree-search input{width:100%;background:#16162a;border:1px solid #333;border-radius:4px;padding:6px 10px;color:#ccc;font-size:12px;outline:none}
#tree-search input:focus{border-color:#64ffda44}
.search-result{padding:6px 14px;font-size:11px;color:#aaa;cursor:pointer;border-bottom:1px solid #222;transition:background .1s}
.search-result:hover{background:rgba(100,255,218,0.06);color:#ddd}
.search-result.active{background:rgba(100,255,218,0.12);color:#64ffda;border-left:2px solid #64ffda}
.search-result .sr-wing{color:#64ffda;font-size:10px;font-weight:600}
.search-result .sr-room{color:#888;font-size:10px}
.search-result .sr-sim{color:#555;font-size:9px;float:right}
.search-result .sr-snippet{color:#999;font-size:11px;display:block;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:250px}
.search-info{padding:8px 14px;font-size:11px;color:#555;text-align:center}
.search-searching{padding:8px 14px;font-size:11px;color:#555;text-align:center}
.search-searching::after{content:'';display:inline-block;width:10px;height:10px;border:2px solid #555;border-top-color:#64ffda;border-radius:50%;animation:spinner .6s linear infinite;margin-left:6px;vertical-align:middle}
@keyframes spinner{to{transform:rotate(360deg)}}
.search-clear{color:#64ffda;cursor:pointer;font-size:11px;margin-left:6px}
.search-clear:hover{text-decoration:underline}
#tree-scroll{flex:1;overflow-y:auto;padding:4px 0}
#tree-scroll::-webkit-scrollbar{width:4px}
#tree-scroll::-webkit-scrollbar-thumb{background:#333;border-radius:2px}
.wing-item{cursor:pointer;user-select:none}
.wing-header{padding:6px 14px;display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:#ccc;transition:background .1s;position:relative}
.wing-header:hover{background:rgba(100,255,218,0.06);color:#fff}
.arrow{color:#555;font-size:10px;transition:transform .15s;width:12px;flex-shrink:0;display:inline-block}
.arrow.open{transform:rotate(90deg)}
.wing-header .wing-count{color:#555;font-size:10px;margin-left:auto}
.wing-menu-btn{color:#555;font-size:14px;cursor:pointer;padding:0 6px;font-weight:400;line-height:1;position:relative;user-select:none}
.wing-menu-btn:hover{color:#64ffda}
.wing-menu{position:absolute;right:0;top:100%;background:rgba(30,30,55,0.98);border:1px solid #444;border-radius:6px;min-width:130px;z-index:200;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.4)}
.wing-menu.open{display:block}
.wing-menu-item{padding:6px 12px;font-size:12px;color:#ccc;cursor:pointer;white-space:nowrap}
.wing-menu-item:hover{background:rgba(100,255,218,0.1);color:#64ffda}
.room-item{padding:3px 14px 3px 32px;display:flex;align-items:center;gap:6px;font-size:12px;color:#888;cursor:pointer;transition:background .1s;position:relative}
.room-item:hover{background:rgba(100,255,218,0.04);color:#ccc}
.room-menu-btn{color:#444;font-size:13px;cursor:pointer;padding:0 4px;font-weight:400;line-height:1;position:relative;user-select:none;margin-left:auto}
.room-menu-btn:hover{color:#64ffda}
.room-menu{position:absolute;right:0;top:100%;background:rgba(30,30,55,0.98);border:1px solid #444;border-radius:6px;min-width:120px;z-index:200;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.4)}
.room-menu.open{display:block}
.room-menu-item{padding:6px 12px;font-size:12px;color:#ccc;cursor:pointer;white-space:nowrap}
.room-menu-item:hover{background:rgba(100,255,218,0.1);color:#64ffda}
.room-item .room-count{color:#555;font-size:10px;margin-left:auto}
.room-item.active{color:#64ffda;background:rgba(100,255,218,0.06)}
.room-drawers{overflow:visible}
.drawer-item{padding:4px 14px 4px 48px;font-size:11px;color:#666;cursor:pointer;transition:background .1s;display:flex;align-items:center;gap:6px;position:relative}
.drawer-item:hover{background:rgba(100,255,218,0.06);color:#bbb}
.drawer-menu-btn{color:#444;font-size:12px;cursor:pointer;padding:0 3px;font-weight:400;line-height:1;position:relative;user-select:none;margin-left:auto}
.drawer-menu-btn:hover{color:#ff5252}
.drawer-menu{position:absolute;right:0;top:100%;background:rgba(30,30,55,0.98);border:1px solid #444;border-radius:6px;min-width:100px;z-index:300;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.4)}
.drawer-menu.open{display:block}
.drawer-menu-item{padding:5px 10px;font-size:11px;color:#ccc;cursor:pointer;white-space:nowrap}
.drawer-menu-item:hover{background:rgba(255,82,82,0.1);color:#ff5252}
.drawer-item.active{background:rgba(100,255,218,0.08);color:#64ffda}
.drawer-item .src{color:#555;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:130px}
.drawer-item:hover .src{color:#888}
.drawer-item.active .src{color:#64ffda}
.wing-match{background:rgba(100,255,218,0.08)}
.wing-match>.wing-header{color:#64ffda}
.wing-match>.wing-header .arrow{color:#64ffda}
#info{position:fixed;left:280px;bottom:0;right:0;height:50vh;display:none;z-index:100;background:rgba(22,22,42,0.98);border-top:1px solid #444;flex-direction:column;font-size:13px;line-height:1.5;box-shadow:0 -4px 24px rgba(0,0,0,0.5)}
#info.alone{left:0}
#info.open{display:flex}
#info-header{display:flex;align-items:center;flex-shrink:0;background:rgba(22,22,42,0.98)}
#info-tabs{display:flex;flex:1;border-bottom:1px solid #333}
.info-tab{padding:10px 16px;font-size:11px;font-weight:600;color:#666;cursor:pointer;border-bottom:2px solid transparent;transition:all .1s;user-select:none}
.info-tab:hover{color:#999}
.info-tab.active{color:#64ffda;border-bottom-color:#64ffda}
#info-close{padding:8px 16px;cursor:pointer;color:#666;font-size:22px;line-height:1;transition:color .1s}
#info-close:hover{color:#fff}
#info-content{padding:14px;flex:1;overflow-y:auto}
#info-content::-webkit-scrollbar{width:4px}
#info-content::-webkit-scrollbar-thumb{background:#444;border-radius:2px}
.entity-type{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.section{margin-top:12px}
.section h4{font-size:11px;font-weight:700;color:#888;margin:0 0 6px;text-transform:uppercase;letter-spacing:1px}
.conn-item{display:flex;align-items:center;gap:6px;padding:4px 8px;border-radius:4px;cursor:pointer;transition:background .15s;margin:1px 0;font-size:12px}
.conn-item:hover{background:rgba(100,255,218,0.08)}
.predicate-label{color:#777;font-size:10px;font-style:italic;flex-shrink:0}
.props-table{width:100%;font-size:12px}
.props-table td{padding:2px 8px;vertical-align:top}
.props-table td:first-child{color:#888;white-space:nowrap;width:1px}
.props-table td:last-child{color:#ccc;word-break:break-all}
.legend-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:middle}
.nav-link{color:#64ffda;cursor:pointer}
.nav-link:hover{text-decoration:underline}
.closet-badge{color:#888;font-size:10px;background:rgba(255,255,255,0.06);padding:1px 6px;border-radius:3px}
#legend{position:fixed;bottom:16px;left:296px;background:rgba(26,26,46,0.92);border:1px solid #333;border-radius:8px;padding:8px 12px;z-index:40;font-size:10px;line-height:1.8;display:flex;flex-wrap:wrap;gap:2px 8px}
.info-open #legend{bottom:calc(50vh + 16px)}
.loading-bar{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:#555;font-size:13px}
.markdown-viewer pre{background:#16162a;padding:8px 12px;border-radius:6px;overflow-x:auto;font-size:11px;color:#abb2bf;margin:6px 0}
.markdown-viewer code{background:#16162a;padding:1px 4px;border-radius:3px;font-size:11px;color:#ffcb6b}
.markdown-viewer h1{color:#64ffda;font-size:16px;font-weight:700;margin:14px 0 6px}
.markdown-viewer h2{color:#e0e0e0;font-size:14px;font-weight:600;margin:12px 0 4px;border-bottom:1px solid #333;padding-bottom:2px}
.markdown-viewer h3{color:#ccc;font-size:13px;font-weight:600;margin:10px 0 4px}
.markdown-viewer p{margin:4px 0}
.markdown-viewer ul{padding-left:18px;margin:4px 0}
.markdown-viewer li{color:#bbb;font-size:12px;margin:1px 0}
</style>
</head>
<body>
<div id="login-overlay" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);justify-content:center;align-items:center">
  <div style="background:#1a1a2e;border:1px solid #333;border-radius:12px;padding:32px;width:360px;box-shadow:0 8px 32px rgba(0,0,0,0.5)">
    <h2 style="color:#64ffda;margin-bottom:8px;font-size:18px">MemPalace Auth</h2>
    <p style="color:#888;font-size:12px;margin-bottom:20px">Enter credentials to access the knowledge graph</p>
    <input id="login-user" type="text" placeholder="Username" style="width:100%;background:#16162a;border:1px solid #333;border-radius:6px;padding:10px 12px;color:#ccc;font-size:14px;margin-bottom:10px;outline:none" autocomplete="username">
    <input id="login-pass" type="password" placeholder="Password" style="width:100%;background:#16162a;border:1px solid #333;border-radius:6px;padding:10px 12px;color:#ccc;font-size:14px;margin-bottom:20px;outline:none" autocomplete="current-password">
    <div id="login-error" style="color:#ff6b6b;font-size:12px;margin-bottom:10px;display:none"></div>
    <button id="login-btn" style="width:100%;background:#64ffda;color:#0a0a1a;border:none;border-radius:6px;padding:10px;font-size:14px;font-weight:600;cursor:pointer">Login</button>
  </div>
</div>
<div id="sidebar-toggle" onclick="toggleSidebar()">&#9776;</div>
<div id="sidebar">
  <div id="tree-header">
    <h2>&#x1f9e0; Palace</h2>
    <span id="tree-stats">loading...</span>
  </div>
  <div id="tree-search"><input type="text" placeholder="semantic search..." oninput="semanticSearch(this.value)" onkeydown="if(event.key==='Enter'){event.preventDefault();if(searchTimeout)clearTimeout(searchTimeout);doSearch(this.value.trim())}" id="search-input"></div>
  <div id="tree-scroll"></div>
</div>
<div id="graph">
  <div class="loading-bar" id="loading-msg">loading graph...</div>
</div>
<div id="info">
  <div id="info-header">
    <div id="info-tabs">
      <div class="info-tab active" data-tab="detail" onclick="switchTab('detail')">Detail</div>
      <div class="info-tab" data-tab="content" onclick="switchTab('content')">Content</div>
    </div>
    <div id="info-close" onclick="closeInfo()">&times;</div>
  </div>
  <div id="info-content"></div>
</div>
<div id="legend"></div>
<script>
var COLORS={person:"#4CAF50",project:"#2196F3",artifact:"#FF9800",concept:"#9C27B0",tool:"#F44336",location:"#00BCD4",event:"#795548",unknown:"#607D8B"};
var TYPE_LABELS={person:"Person",project:"Project",artifact:"Artifact",concept:"Concept",tool:"Tool",location:"Location",event:"Event",unknown:"Unknown"};
var network=null,nodeDataSet=null,palaceData=null,infoData=null,infoMode='detail';

function esc(s){if(!s)return '';var d=document.createElement('div');d.textContent=String(s);return d.innerHTML}
function closeInfo(){document.getElementById('info').classList.remove('open');document.getElementById('graph').classList.remove('info-open')}
function toggleSidebar(){var s=document.getElementById('sidebar'),g=document.getElementById('graph'),i=document.getElementById('info');s.classList.toggle('hidden');g.classList.toggle('alone');i.classList.toggle('alone')}
function switchTab(t){infoMode=t;document.querySelectorAll('.info-tab').forEach(function(x){x.classList.toggle('active',x.dataset.tab===t)});renderInfo()}

function showLoading(){document.getElementById('loading-msg').textContent='loading graph...'}
function hideLoading(){document.getElementById('loading-msg').style.display='none'}

// ── Palace tree ────────────────────────────────────────
function loadPalaceTree(){
  fetch('/api/palace').then(function(r){return r.json()}).then(function(data){
    palaceData=data;
    document.getElementById('tree-stats').textContent=data.total_drawers+' drawers';
    renderTree(data.wings);
  })
}
function renderTree(wings){
  var html='';
  for(var wi=0;wi<wings.length;wi++){
    var w=wings[wi];
    html+='<div class="wing-item" data-wing="'+esc(w.name)+'">';
    html+='<div class="wing-header" onclick="toggleWing(this)"><span class="arrow">&#9654;</span>'+esc(w.name)+'<span class="wing-menu-btn" onclick="event.stopPropagation();toggleMenu(this,\\'wing-menu\\')">&#x22EE;</span><span class="wing-count">'+w.rooms.length+' rooms</span><div class="wing-menu"><div class="wing-menu-item" onclick="event.stopPropagation();mergeWing(\\''+esc(w.name)+'\\')">Merge into...</div><div class="wing-menu-item" onclick="event.stopPropagation();dedupeWing(\\''+esc(w.name)+'\\')">Dedup drawers</div><div class="wing-menu-item" onclick="event.stopPropagation();deleteWing(\\''+esc(w.name)+'\\')" style="color:#ff5252">Delete wing</div></div></div>';
    html+='<div class="wing-rooms" style="display:none">';
    for(var ri=0;ri<w.rooms.length;ri++){
      var r=w.rooms[ri];
      html+='<div class="room-item" onclick="toggleRoom(this)" data-wing="'+esc(w.name)+'" data-room="'+esc(r.name)+'" data-loaded="false"><span class="arrow">&#9654;</span><span class="legend-dot" style="background:#555"></span>'+esc(r.name)+'<span class="room-menu-btn" onclick="event.stopPropagation();toggleMenu(this,\\'room-menu\\')">&#x22EE;</span><span class="room-count">'+r.drawer_count+'</span><div class="room-menu"><div class="room-menu-item" onclick="event.stopPropagation();deleteRoom(\\''+esc(w.name)+'\\',\\''+esc(r.name)+'\\')" style="color:#ff5252">Delete room</div></div></div>';
      html+='<div class="room-drawers" style="display:none"></div>';
    }
    html+='</div></div>';
  }
  document.getElementById('tree-scroll').innerHTML=html;
}
function toggleWing(el){
  var arrow=el.querySelector('.arrow');
  var rooms=el.parentElement.querySelector('.wing-rooms');
  var isOpen=rooms.style.display!='none';
  rooms.style.display=isOpen?'none':'block';
  arrow.classList.toggle('open',!isOpen);
  if(!isOpen){
    var wingItem=el.parentElement;
    focusGraphWing(wingItem.dataset.wing);
  }else{
    nodeDataSet.clear();
    edgeDataSet.clear();
    expanded={};
  }
}
function focusGraphRoom(wingName,roomName){
  var wingNodeId='wing:'+wingName;
  var roomNodeId='room:'+wingName+'/'+roomName;
  if(!nodeDataSet.get(wingNodeId))focusGraphWing(wingName);
  var roomNode=nodeDataSet.get(roomNodeId);
  if(roomNode&&!expanded[roomNodeId])handleRoomClick(roomNode);
}

function toggleRoom(el){
  var arrow=el.querySelector('.arrow');
  var drawers=el.nextElementSibling;
  if(!drawers||!drawers.classList.contains('room-drawers'))return;
  var isOpen=drawers.style.display!='none';
  if(isOpen){
    drawers.style.display='none';
    arrow.classList.remove('open');
    return;
  }
  arrow.classList.add('open');
  drawers.style.display='block';
  focusGraphRoom(el.dataset.wing,el.dataset.room);
  // lazy-load drawers
  if(el.dataset.loaded==='false'){
    el.dataset.loaded='true';
    var wing=el.dataset.wing,room=el.dataset.room;
    drawers.innerHTML='<div style="padding:8px 14px 4px 48px;font-size:11px;color:#555">loading...</div>';
    fetch('/api/drawers?wing='+encodeURIComponent(wing)+'&room='+encodeURIComponent(room)+'&limit=50')
      .then(function(r){return r.json()})
      .then(function(data){
        if(!data.drawers||!data.drawers.length){
          drawers.innerHTML='<div style="padding:8px 14px 4px 48px;font-size:11px;color:#444">no drawers</div>';
          return;
        }
        var dh='';
        for(var i=0;i<data.drawers.length;i++){
          var d=data.drawers[i];
          var src=d.source?d.source.split('/').pop():d.content.slice(0,28)+'…'+d.id.slice(-6);
          dh+='<div class="drawer-item" onclick="showDrawerContent(\\''+esc(wing)+'\\',\\''+esc(room)+'\\',\\''+esc(d.id)+'\\',this)" data-id="'+esc(d.id)+'">';
          dh+='<span style="color:#555;font-size:10px;">&#x1f4c4;</span>';
          dh+='<span class="src">'+esc(src)+'</span>';
          dh+='<span class="drawer-menu-btn" onclick="event.stopPropagation();toggleMenu(this,\\'drawer-menu\\')">&#x22EE;</span>';
          dh+='<div class="drawer-menu"><div class="drawer-menu-item" onclick="event.stopPropagation();deleteDrawerById(\\''+esc(d.id)+'\\')" style="color:#ff5252">Delete</div></div>';
          dh+='</div>';
        }
        drawers.innerHTML=dh;
      })
      .catch(function(){
        drawers.innerHTML='<div style="padding:8px 14px 4px 48px;font-size:11px;color:#f44336">error loading</div>';
      });
  }
}
function showDrawerContent(wing,room,id,el){
  document.querySelectorAll('.drawer-item.active').forEach(function(x){x.classList.remove('active')});
  if(el)el.classList.add('active');
  showInfo();
  showTab('content');
  document.getElementById('info-content').innerHTML='<div style="color:#666;text-align:center;padding:20px">loading...</div>';
  fetch('/api/drawers?wing='+encodeURIComponent(wing)+'&room='+encodeURIComponent(room)+'&limit=50')
    .then(function(r){return r.json()})
    .then(function(data){
      if(!data.drawers||!data.drawers.length){
        document.getElementById('info-content').innerHTML='<p style="color:#666;text-align:center;padding:20px">No content</p>';
        return;
      }
      // find the specific drawer by id
      var drawer=null;
      for(var i=0;i<data.drawers.length;i++){
        if(data.drawers[i].id===id){drawer=data.drawers[i];break}
      }
      if(!drawer)drawer=data.drawers[0];
      var label=drawer.source?drawer.source.split('/').pop():drawer.content.slice(0,28)+'…'+drawer.id.slice(-6);
      var html='<div style="margin-bottom:8px">';
      html+='<span style="color:#64ffda;font-size:12px;font-weight:600">'+esc(wing)+' / '+esc(room)+'</span>';
      html+=' <span style="color:#555;font-size:11px">'+esc(label)+'</span>';
      html+='</div><div class="markdown-viewer">'+renderMarkdown(drawer.content)+'</div>';
      document.getElementById('info-content').innerHTML=html;
    })
    .catch(function(err){
      document.getElementById('info-content').innerHTML='<p style="color:#f44336;">'+err.message+'</p>';
    });
}
var searchTimeout=null,lastSearch='';
function semanticSearch(val){
  if(searchTimeout)clearTimeout(searchTimeout);
  if(!val.trim()){
    lastSearch='';
    document.getElementById('tree-scroll').innerHTML='';
    loadPalaceTree();
    return;
  }
  document.getElementById('tree-scroll').innerHTML='<div class="search-searching">searching</div>';
  searchTimeout=setTimeout(function(){doSearch(val.trim())},300);
}
function doSearch(q){
  if(q===lastSearch)return;
  lastSearch=q;
  document.getElementById('tree-scroll').innerHTML='<div class="search-searching">searching</div>';
  fetch('/api/palace/search?q='+encodeURIComponent(q)+'&limit=30')
    .then(function(r){return r.json()})
    .then(function(data){
      var el=document.getElementById('tree-scroll');
      if(data.error){el.innerHTML='<div class="search-info">Error: '+esc(data.error)+'</div>';return}
      if(!data.results||!data.results.length){
        el.innerHTML='<div class="search-info">No results for "'+esc(q)+'"</div>';
        return;
      }
      var html='<div class="search-info">'+data.results.length+' result(s) for "'+esc(q)+'" <span class="search-clear" onclick="clearSearch()">clear</span></div>';
      for(var i=0;i<data.results.length;i++){
        var r=data.results[i];
        var snippet=r.content.replace(/\\n/g,' ').slice(0,200);
        var pct=Math.round(r.similarity*100);
        html+='<div class="search-result" onclick="navToResult(event,\\''+esc(r.id)+'\\',\\''+esc(r.wing)+'\\',\\''+esc(r.room)+'\\')">';
        html+='<span class="sr-wing">'+esc(r.wing)+'</span> / <span class="sr-room">'+esc(r.room)+'</span>';
        html+='<span class="sr-sim">'+pct+'%</span>';
        html+='<span class="sr-snippet">'+esc(snippet)+'</span>';
        html+='</div>';
      }
      el.innerHTML=html;
    })
    .catch(function(err){
      document.getElementById('tree-scroll').innerHTML='<div class="search-info">Error: '+err.message+'</div>';
    });
}
function clearSearch(){
  document.getElementById('search-input').value='';
  lastSearch='';
  if(searchTimeout)clearTimeout(searchTimeout);
  document.getElementById('tree-scroll').innerHTML='';
  loadPalaceTree();
}
function navToResult(evt,id,wing,room){
  document.querySelectorAll('.search-result.active').forEach(function(x){x.classList.remove('active')});
  var el=evt&&evt.target?evt.target.closest('.search-result'):null;
  if(el)el.classList.add('active');
  showInfo();showTab('content');
  document.getElementById('info-content').innerHTML='<div style="color:#666;text-align:center;padding:20px">loading...</div>';
  fetch('/api/drawer/'+encodeURIComponent(id))
    .then(function(r){return r.json()})
    .then(function(drawer){
      if(drawer.error){document.getElementById('info-content').innerHTML='<p style="color:#f44336;">'+esc(drawer.error)+'</p>';return}
      var label=drawer.source?drawer.source.split('/').pop():drawer.content.slice(0,28)+'…'+drawer.id.slice(-6);
      var html='<div style="margin-bottom:8px"><span style="color:#64ffda;font-size:12px;font-weight:600">'+esc(drawer.wing)+' / '+esc(drawer.room)+'</span> <span style="color:#555;font-size:11px">'+esc(label)+'</span></div><div class="markdown-viewer">'+renderMarkdown(drawer.content)+'</div>';
      document.getElementById('info-content').innerHTML=html;
    })
    .catch(function(err){
      document.getElementById('info-content').innerHTML='<p style="color:#f44336;">'+err.message+'</p>';
    });
}
function mergeWing(source){
  var target=prompt('Merge "'+source+'" into which wing?');
  if(!target||target.trim()===source)return;
  target=target.trim();
  fetch('/api/palace/merge?source='+encodeURIComponent(source)+'&target='+encodeURIComponent(target),{method:'POST'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert('Error: '+d.error);return}
      refreshGraph();
      loadPalaceTree();
    })
    .catch(function(err){alert('Merge failed: '+err.message)});
}
function dedupeWing(wingName){
  var msg='Remove duplicate drawers in "'+wingName+'"?';
  if(!confirm(msg))return;
  fetch('/api/palace/dedupe?wing='+encodeURIComponent(wingName),{method:'POST'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert('Error: '+d.error);return}
      if(d.removed)alert('Removed '+d.removed+' duplicate(s)');
      else alert('No duplicates found ('+d.kept+' unique drawer(s))');
      refreshGraph();
      loadPalaceTree();
    })
    .catch(function(err){alert('Dedupe failed: '+err.message)});
}
function deleteWing(wingName){
  var msg='Delete entire wing "'+wingName+'" and all its drawers?';
  if(!confirm(msg))return;
  fetch('/api/palace/delete-wing?wing='+encodeURIComponent(wingName),{method:'POST'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert('Error: '+d.error);return}
      refreshGraph();
      loadPalaceTree();
    })
    .catch(function(err){alert('Delete failed: '+err.message)});
}
function deleteRoom(wingName,roomName){
  var msg='Delete room "'+roomName+'" and all its drawers?';
  if(!confirm(msg))return;
  fetch('/api/palace/delete-room?wing='+encodeURIComponent(wingName)+'&room='+encodeURIComponent(roomName),{method:'POST'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert('Error: '+d.error);return}
      refreshGraph();
      loadPalaceTree();
    })
    .catch(function(err){alert('Delete failed: '+err.message)});
}
function deleteDrawerById(id){
  if(!id||!confirm('Delete this drawer?'))return;
  fetch('/api/palace/delete-drawer?id='+encodeURIComponent(id),{method:'POST'})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.error){alert('Error: '+d.error);return}
      refreshGraph();
      loadPalaceTree();
    })
    .catch(function(err){alert('Delete failed: '+err.message)});
}
function toggleMenu(btn,cls){
  var menu=btn.parentElement.querySelector('.'+cls);
  if(!menu)return;
  document.querySelectorAll('.'+cls+'.open').forEach(function(m){if(m!==menu)m.classList.remove('open')});
  menu.classList.toggle('open');
}

// ── Markdown renderer (uses marked.js) ───────────────────
function renderMarkdown(text){
  if(!text)return '';
  return marked.parse(text,{gfm:true,breaks:true});
}

// ── Info panel ──────────────────────────────────────────
function showInfo(){document.getElementById('info').classList.add('open');document.getElementById('graph').classList.add('info-open')}
function showTab(t){switchTab(t);showInfo()}

function renderInfo(){
  var el=document.getElementById('info-content');
  if(!infoData){el.innerHTML='<p style="color:#666;text-align:center;padding:20px;">No data</p>';return}
  if(infoMode==='detail'){
    if(infoData.entity)renderEntityDetail(infoData);
    else if(infoData.triple)renderTripleDetail(infoData);
    else el.innerHTML='<p style="color:#666">No detail available</p>';
  }else if(infoMode==='content'){
    if(infoData.drawersHtml)el.innerHTML=infoData.drawersHtml;
    else el.innerHTML='<p style="color:#666;text-align:center;padding:20px;">No content</p>';
  }
}

function renderEntityDetail(data){
  var e=data.entity;
  if(!e){document.getElementById('info-content').innerHTML='<p style="color:#f44336;">Entity not found</p>';return}
  var tc=COLORS[e.type]||COLORS['unknown'];
  var html='<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">';
  html+='<span class="legend-dot" style="background:'+tc+';width:14px;height:14px"></span>';
  html+='<h3 style="margin:0;font-size:16px;font-weight:600;color:#fff">'+esc(e.name)+'</h3>';
  html+='<span class="entity-type" style="background:'+tc+'22;color:'+tc+';border:1px solid '+tc+'66">'+(TYPE_LABELS[e.type]||e.type)+'</span>';
  html+='</div><div style="color:#555;font-size:11px;margin-bottom:6px">'+esc(e.id)+' &middot; '+esc(e.created_at)+'</div>';

  if(e.properties&&e.properties!='{}'){try{var props=JSON.parse(e.properties);var keys=Object.keys(props);if(keys.length){html+='<div class="section"><h4>Properties</h4><table class="props-table">';for(var i=0;i<keys.length;i++){var k=keys[i],v=props[k];if(typeof v==='object')v=JSON.stringify(v);html+='<tr><td>'+esc(k)+'</td><td>'+esc(v)+'</td></tr>'}html+='</table></div>'}}catch(_){}}

  if(data.closets&&data.closets.length){html+='<div class="section"><h4>Rooms</h4><div style="display:flex;flex-wrap:wrap;gap:4px">';for(var i=0;i<data.closets.length;i++)html+='<span class="closet-badge">'+esc(data.closets[i])+'</span>';html+='</div></div>'}

  if(data.outgoing&&data.outgoing.length){html+='<div class="section"><h4>&rarr; Outgoing ('+data.outgoing.length+')</h4>';for(var i=0;i<data.outgoing.length;i++){var t=data.outgoing[i],on=t.object_name||t.object,ot=t.object_type||'unknown',oc=COLORS[ot]||COLORS['unknown'];html+='<div class="conn-item" onclick="navTo(\\''+esc(t.object)+'\\')"><span class="legend-dot" style="background:'+oc+';flex-shrink:0"></span><span class="nav-link">'+esc(on)+'</span> <span class="predicate-label">'+esc(t.predicate)+'</span>'+(t.source_closet?' <span class="closet-badge">'+esc(t.source_closet)+'</span>':'')+'</div>'}html+='</div>'}

  if(data.incoming&&data.incoming.length){html+='<div class="section"><h4>&larr; Incoming ('+data.incoming.length+')</h4>';for(var i=0;i<data.incoming.length;i++){var t=data.incoming[i],sn=t.subject_name||t.subject,st=t.subject_type||'unknown',sc=COLORS[st]||COLORS['unknown'];html+='<div class="conn-item" onclick="navTo(\\''+esc(t.subject)+'\\')"><span class="legend-dot" style="background:'+sc+';flex-shrink:0"></span><span class="nav-link">'+esc(sn)+'</span> <span class="predicate-label">'+esc(t.predicate)+'</span>'+(t.source_closet?' <span class="closet-badge">'+esc(t.source_closet)+'</span>':'')+'</div>'}html+='</div>'}

  document.getElementById('info-content').innerHTML=html;
}

function renderTripleDetail(data){
  var t=data.triple;
  var html='<div class="section"><h4>Triple Detail</h4>';
  html+='<table class="props-table">';
  html+='<tr><td>subject</td><td class="nav-link" onclick="navTo(\\''+esc(t.subject)+'\\')">'+esc((data.subject||{}).name||t.subject)+'</td></tr>';
  html+='<tr><td>predicate</td><td>'+esc(t.predicate)+'</td></tr>';
  html+='<tr><td>object</td><td class="nav-link" onclick="navTo(\\''+esc(t.object)+'\\')">'+esc((data.object||{}).name||t.object)+'</td></tr>';
  html+='<tr><td>confidence</td><td>'+t.confidence+'</td></tr>';
  if(t.valid_from)html+='<tr><td>valid from</td><td>'+esc(t.valid_from)+'</td></tr>';
  if(t.valid_to)html+='<tr><td>valid to</td><td>'+esc(t.valid_to)+'</td></tr>';
  if(t.source_closet)html+='<tr><td>source</td><td>'+esc(t.source_closet)+'</td></tr>';
  html+='</table></div>';

  if(t.source_file){html+='<div class="section"><h4>Source File</h4><div style="font-size:11px;color:#888">'+esc(t.source_file)+'</div></div>'}

  if(data.source_drawer){html+='<div class="section"><h4>Source Drawer Content</h4><div class="markdown-viewer">'+renderMarkdown(data.source_drawer)+'</div></div>'}

  document.getElementById('info-content').innerHTML=html;
}

// ── Tree sync ──────────────────────────────────────────
function syncTree(entityName){
  if(!entityName)return;
  var wings=document.querySelectorAll('.wing-item');
  var best=null,bestScore=0;
  for(var i=0;i<wings.length;i++){
    var wName=(wings[i].dataset.wing||'').toLowerCase();
    var eName=entityName.toLowerCase();
    var score=0;
    if(wName===eName)score=3;
    else if(wName.includes(eName)||eName.includes(wName))score=2;
    else if(wName.split(/[-\\s_]/).some(function(p){return eName.includes(p)||p.includes(eName)}))score=1;
    if(score>bestScore){bestScore=score;best=wings[i]}
  }
  if(!best)return;
  document.querySelectorAll('.wing-match').forEach(function(x){x.classList.remove('wing-match')});
  var header=best.querySelector('.wing-header'),rooms=best.querySelector('.wing-rooms'),arrow=header.querySelector('.arrow');
  rooms.style.display='block';arrow.classList.add('open');
  best.classList.add('wing-match');
  best.scrollIntoView({block:'center',behavior:'smooth'});
}

function navTo(id){
  infoData=null;
  document.getElementById('info-content').innerHTML='<div style="color:#666;text-align:center;padding:20px;">loading...</div>';
  showInfo();
  showTab('detail');
  fetch('/api/entity/'+encodeURIComponent(id))
    .then(function(r){if(!r.ok)throw new Error('Not found in KG');return r.json()})
    .then(function(data){
      infoData=data;
      syncTree(data.entity&&data.entity.name);
      // also load related drawers
      fetch('/api/drawers?wing='+encodeURIComponent(id)+'&limit=3')
        .then(function(r){return r.json()}).then(function(dd){
          if(dd.drawers&&dd.drawers.length){
            var dh='<div class="section"><h4>Related Palace Content</h4><div class="markdown-viewer">';
            for(var i=0;i<dd.drawers.length;i++)dh+=renderMarkdown(dd.drawers[i].content);
            dh+='</div></div>';
            data.drawersHtml=dh;
          }
          renderInfo();
        }).catch(function(){renderInfo()});
    })
    .catch(function(err){
      document.getElementById('info-content').innerHTML='<p style="color:#f44336;">'+err.message+'</p>';
      showInfo();
    });
}

// ── Graph — palace tree (wings → rooms → drawers) ─────
var expanded={},drawerContents={};

function refreshGraph(){
  fetch('/api/palace').then(function(r){return r.json()}).then(function(data){
    hideLoading();
    palaceData=data;
    expanded={};drawerContents={};
    if(!network){
      nodeDataSet=new vis.DataSet([]);
      edgeDataSet=new vis.DataSet([]);
      var container=document.getElementById('graph');
      var options={physics:{solver:'forceAtlas2Based',forceAtlas2Based:{gravitationalConstant:-80,centralGravity:0.01,springLength:180,springConstant:0.04,damping:0.4},stabilization:{iterations:50}},interaction:{hover:true,tooltipDelay:200,zoomView:true,dragView:true},edges:{smooth:{type:'curvedCW'}}};
      network=new vis.Network(container,{nodes:nodeDataSet,edges:edgeDataSet},options);
      network.on('click',function(p){
        if(p.nodes.length){
          var n=nodeDataSet.get(p.nodes[0]);
          if(!n)return;
          if(n.level==='wing')handleWingClick(n);
          else if(n.level==='room')handleRoomClick(n);
          else if(n.level==='drawer')showDrawerFromGraph(n);
        }else{closeInfo()}
      });
    }else{
      nodeDataSet.clear();
      edgeDataSet.clear();
    }
    document.getElementById('tree-stats').textContent=data.total_drawers+' drawers | '+data.wings.length+' wings';
    document.getElementById('legend').innerHTML='<span class="legend-dot" style="background:#64ffda"></span>wing <span class="legend-dot" style="background:#4CAF50"></span>room <span class="legend-dot" style="background:#FF9800"></span>drawer';
  }).catch(function(err){document.getElementById('loading-msg').textContent='Error: '+err.message});
}
function initGraph(){refreshGraph()}

function focusGraphWing(wingName){
  var wing=palaceData.wings.find(function(w){return w.name===wingName});
  if(!wing)return;
  nodeDataSet.clear();
  edgeDataSet.clear();
  expanded={};
  nodeDataSet.add({
    id:'wing:'+wingName,label:wingName,level:'wing',
    shape:'box',color:{background:'#64ffda',border:'#0a0a1a'},
    font:{color:'#0a0a1a',size:14,bold:true},borderWidth:2,physics:false
  });
  handleWingClick(nodeDataSet.get('wing:'+wingName),true);
}

function handleWingClick(node,skipSync){
  var wName=node.id.slice(5);
  var wing=palaceData.wings.find(function(w){return w.name===wName});
  if(!wing)return;
  if(expanded[node.id]){collapseNode(node.id);return}
  if(!skipSync)syncTree(wName);
  var ns=[],es=[],kids=[];
  wing.rooms.forEach(function(room){
    var rid='room:'+wName+'/'+room.name;
    kids.push(rid);
    ns.push({id:rid,label:room.name,level:'room',shape:'dot',size:20,color:'#4CAF50',font:{color:'#e0e0e0',size:12,strokeWidth:2,strokeColor:'#1a1a2e'},physics:true});
    es.push({from:node.id,to:rid,label:room.drawer_count+'',color:{color:'#64ffda44'},font:{size:10,color:'#555',strokeWidth:2,strokeColor:'#1a1a2e'}});
  });
  nodeDataSet.add(ns);edgeDataSet.add(es);
  expanded[node.id]={children:kids,edges:edgeDataSet.get({filter:function(e){return e.from===node.id}}).map(function(e){return e.id})};
}

function handleRoomClick(node){
  var parts=node.id.slice(5).split('/');
  var wName=parts[0],rName=parts.slice(1).join('/');
  if(expanded[node.id]){collapseNode(node.id);return}
  expanded[node.id]=true;
  fetch('/api/drawers?wing='+encodeURIComponent(wName)+'&room='+encodeURIComponent(rName)+'&limit=20')
    .then(function(r){return r.json()}).then(function(data){
      if(!expanded[node.id])return;
      if(!data.drawers||!data.drawers.length)return;
      var ns=[],es=[],kids=[];
      data.drawers.forEach(function(d){
          var src=d.source?d.source.split('/').pop():d.content.slice(0,12)+'…'+d.id.slice(-6);
        var did='drawer:'+(d.id||wName+'/'+rName+'/'+src);
        kids.push(did);
        drawerContents[did]={wing:wName,room:rName,source:d.source,content:d.content,id:d.id};
        ns.push({id:did,label:src,level:'drawer',shape:'dot',size:10,color:'#FF9800',font:{color:'#888',size:9,strokeWidth:2,strokeColor:'#1a1a2e'},physics:true});
        es.push({from:node.id,to:did,color:{color:'#FF980044'}});
      });
      nodeDataSet.add(ns);edgeDataSet.add(es);
      expanded[node.id]={children:kids,edges:edgeDataSet.get({filter:function(e){return e.from===node.id}}).map(function(e){return e.id})};
    });
}

function collapseNode(nodeId){
  var entry=expanded[nodeId];
  if(!entry)return;
  entry.children.forEach(function(cid){collapseNode(cid)});
  nodeDataSet.remove(entry.children);
  edgeDataSet.remove(entry.edges);
  delete expanded[nodeId];
}

function showDrawerFromGraph(node){
  var dc=drawerContents[node.id];
  if(!dc)return;
  var src=dc.source?dc.source.split('/').pop():dc.content.slice(0,28)+'…'+dc.id.slice(-6);
  showInfo();showTab('content');
  document.getElementById('info-content').innerHTML=
    '<div style="margin-bottom:8px"><span style="color:#64ffda;font-size:12px;font-weight:600">'+esc(dc.wing)+' / '+esc(dc.room)+
    '</span> <span style="color:#555;font-size:11px">'+esc(src)+'</span></div>'+
    '<div class="markdown-viewer">'+renderMarkdown(dc.content)+'</div>';
}

function showEdgeDetail(edgeId){
  infoData=null;
  document.getElementById('info-content').innerHTML='<div style="color:#666;text-align:center;padding:20px;">loading...</div>';
  showInfo();
  showTab('detail');
  fetch('/api/triple/'+encodeURIComponent(edgeId))
    .then(function(r){if(!r.ok)throw new Error('Triple not found');return r.json()})
    .then(function(data){
      infoData=data;
      renderInfo();
    })
    .catch(function(err){
      document.getElementById('info-content').innerHTML='<p style="color:#f44336;">'+err.message+'</p>';
    });
}

// ── Auth ─────────────────────────────────────────────────
var _authHeader=sessionStorage.getItem('mempalace_auth');
var _origFetch=window.fetch.bind(window);
window.fetch=function(u,o){
  o=o||{};
  if(_authHeader){
    o.headers=o.headers||{};
    if(!o.headers.Authorization) o.headers.Authorization=_authHeader;
  }
  return _origFetch(u,o).then(function(r){
    if(r.status===401){
      _authHeader=null;
      sessionStorage.removeItem('mempalace_auth');
      showLogin();
      return Promise.reject(new Error('Unauthorized'));
    }
    return r;
  });
};
function showLogin(){
  var ov=document.getElementById('login-overlay');
  ov.style.display='flex';
  document.getElementById('login-user').focus();
}
function doLogin(){
  var u=document.getElementById('login-user').value.trim();
  var p=document.getElementById('login-pass').value;
  var err=document.getElementById('login-error');
  if(!u||!p){err.textContent='Both fields required';err.style.display='block';return}
  err.style.display='none';
  _authHeader='Basic '+btoa(u+':'+p);
  sessionStorage.setItem('mempalace_auth',_authHeader);
  document.getElementById('login-overlay').style.display='none';
  refreshGraph();loadPalaceTree();
}
document.getElementById('login-btn').addEventListener('click',doLogin);
document.getElementById('login-pass').addEventListener('keydown',function(e){if(e.key==='Enter')doLogin()});
if(!_authHeader) showLogin();

// ── Live updates via SSE ────────────────────────────────
var evtSource=new EventSource('/events');
evtSource.addEventListener('update',function(e){refreshGraph();loadPalaceTree()});

// ── Close wing menus on outside click ───────────────────
document.addEventListener('click',function(e){
  if(!e.target.closest('.wing-menu-btn,.wing-menu,.room-menu-btn,.room-menu,.drawer-menu-btn,.drawer-menu'))
    document.querySelectorAll('.wing-menu.open,.room-menu.open,.drawer-menu.open').forEach(function(m){m.classList.remove('open')});
});

// ── Boot ────────────────────────────────────────────────
loadPalaceTree();
initGraph();
</script>
</body>
</html>
"""