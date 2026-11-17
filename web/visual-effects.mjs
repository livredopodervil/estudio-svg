// Shared media appearance: one contract for editor/player/HTML and Canvas export.
const clamp=(x,min,max)=>Math.max(min,Math.min(max,Number(x)||0));
export function appearance(o={}){
 const color=c=>typeof c==='string'&&/^#[\da-fA-F]{6}$/.test(c)?c:'#ffffff';
 return {radius:clamp(o.corner_radius,0,.5),border:clamp(o.border_width,0,20),borderColor:color(o.border_color),shadow:clamp(o.shadow_blur,0,60),shadowColor:color(o.shadow_color||'#000000')};
}
export function cssAppearance(o={}){
 const v=appearance(o);
 return {borderRadius:(v.radius*100)+'%',border:v.border?`${v.border}px solid ${v.borderColor}`:'none',boxShadow:v.shadow?`0 4px ${v.shadow}px ${v.shadowColor}`:'none'};
}
export function canvasAppearance(ctx,w,h,o={}){
 const v=appearance(o),r=Math.min(w,h)*v.radius;
 ctx.beginPath();
 if(typeof ctx.roundRect==='function')ctx.roundRect(-w/2,-h/2,w,h,r);
 else ctx.rect(-w/2,-h/2,w,h);
 if(v.shadow){ctx.save();ctx.shadowColor=v.shadowColor;ctx.shadowBlur=v.shadow;ctx.shadowOffsetY=4;ctx.fillStyle='rgba(0,0,0,0.01)';ctx.fill();ctx.restore();}
 ctx.clip();
 return ()=>{if(!v.border)return;ctx.lineWidth=v.border;ctx.strokeStyle=v.borderColor;ctx.stroke();};
}
