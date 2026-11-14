/* Liste des éditions. */
function vEditions(){
  var js=(ED.toutes||[]).slice().reverse();
  var h='<p class="crumb"><a href="#/">Sujets</a> / Éditions</p><h1 tabindex="-1" id="h1">Toutes les éditions</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">Une édition par jour. Chacune garde les sujets, les titres et les analyses tels qu’ils ont été publiés ce jour-là.</p>';
  h+=js.length?'<ul class="eds">'+js.map(function(j){return '<li><a href="'+edUrl(j)+'"'+(j===ED.jour?' aria-current="true"':'')+'>'+esc(jourLong(j))+'</a>'+(j===ED.jour?' <span class="mono mute">vous y êtes</span>':'')+'</li>';}).join('')+'</ul>':'<p class="vide">Aucune édition gardée.</p>';
  return h;
}
