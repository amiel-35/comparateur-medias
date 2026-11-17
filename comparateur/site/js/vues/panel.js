/* panel : les résultats publiés des questionnaires du panel (PANEL, lu dans D.panel, facultatif). Des comptages par
   bord déclaré, faits par une formule à la clôture (urne.resultats) ; un bord sous 5 réponses n'est pas montré. Aucun
   modèle ne lit une réponse. Rien n'est inventé quand il n'y a rien. */
function vPanel(){
  var n=PANEL.length;
  var h='<h1 tabindex="-1" id="h1">'+(n?(n>1?'Ce que le panel a répondu à '+n+' questionnaires':'Ce que le panel a répondu à un questionnaire'):'Le panel n’a encore publié aucun résultat')+'</h1>'+
  '<p class="lede" style="font-family:var(--serif);font-size:1.2rem;max-width:56ch">Des volontaires répondent à quelques questions, sans leur nom. Les résultats ne paraissent qu’après la clôture de chaque questionnaire, bord par bord.</p>'+
  '<p class="etq">Panel de volontaires. Ce n’est pas un sondage.</p>';
  if(!n)h+='<p class="masked">Aucun questionnaire n’est clos pour l’instant. Les résultats paraîtront ici.</p>';
  PANEL.forEach(function(q){
    var ef=q.effectifs||{};
    h+='<h2>'+esc(q.titre||q.questionnaire||'Questionnaire')+'</h2>'+
    '<p class="note">'+pl(q.delivres||0,'membre l’a commencé','membres l’ont commencé')+', '+pl(q.recues||0,'réponse est arrivée','réponses sont arrivées')+'. Il ne peut pas y avoir plus de réponses que de questionnaires commencés.'+
    (q.scellement?' Empreinte des réponses, prise à la clôture : <span class="pn-s">'+esc(q.scellement)+'</span>.':'')+'</p>';
    (q.questions||[]).forEach(function(x){
      var par=x.par_bord||{};
      h+='<h3 class="pn-q">'+esc(x.texte)+(x.profil?' <span class="mute">(question de profil)</span>':'')+'</h3>';
      h+='<table class="pnt"><thead><tr><th scope="col">Réponse</th>'+COTES.map(function(g){
        var p=par[g]||{};
        return '<th scope="col">'+GL[g]+'<small>'+(p.reponses?pl(p.reponses,'réponse','réponses')+', '+(p.statut==='publiable'?'publiable':'indicatif'):'moins de 5 réponses')+'</small></th>';
      }).join('')+'</tr></thead><tbody>'+(x.choix||[]).map(function(c,i){
        return '<tr><th scope="row">'+esc(c)+'</th>'+COTES.map(function(g){
          var p=par[g]||{};
          if(!p.reponses||!p.par_choix)return '<td class="mute">non montré</td>';
          var v=p.par_choix[i]||0;
          return '<td>'+v+' <span class="mute">('+Math.round(v/p.reponses*100)+' %)</span></td>';
        }).join('')+'</tr>';
      }).join('')+'</tbody></table>';
    });
    if(ef.g===null||ef.c===null||ef.d===null)h+='<p class="note">« Non montré » : moins de cinq réponses dans ce bord. Avec si peu de monde, une réponse pourrait désigner quelqu’un.</p>';
  });
  h+='<p class="note">Bords : celui que chaque répondant déclare, de la gauche à la droite, envoyé avec ses réponses et jamais avec son nom. « Indicatif » : moins de dix réponses dans ce bord.</p>';
  if(AV)h+='<h2>La lecture à l’aveugle</h2><p>Le panel lit aussi des titres sans le nom de leur média. Sa lecture s’affiche à côté du classement FrIdéo, sans s’y mêler. <a href="#/classement">Voir la page Classement</a>.</p>';
  return h;
}
