// Mathematical layer: local pixel coordinates, origin at the rectangle center.
// No renderer, DOM, timeline or platform dependency.
export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function affine(p,w,h){
 const r=(p.rz||0)*Math.PI/180,a=Math.cos(r),b=Math.sin(r),s=p.shear||0,c=a*s-b,d=b*s+a;
 const x=(p.pivot_x||0)*w,y=(p.pivot_y||0)*h;
 return [a,b,c,d,x-a*x-c*y,y-b*x-d*y];
}
export function point(m,x,y){return {x:m[0]*x+m[2]*y+m[4],y:m[1]*x+m[3]*y+m[5]};}
export function inverseVector(m,x,y){const det=m[0]*m[3]-m[1]*m[2];if(Math.abs(det)<1e-12)throw Error('Transformação singular');return {x:(m[3]*x-m[2]*y)/det,y:(-m[1]*x+m[0]*y)/det};}
export function geometry(p,W,H){const w=p.w*W,h=p.h*H,m=affine(p,w,h);const at=(x,y)=>{const q=point(m,x*w/2,y*h/2);return {x:q.x+p.x*W,y:q.y+p.y*H};};return {w,h,m,at,pivot:at(2*(p.pivot_x||0),2*(p.pivot_y||0))};}
export function dragPose(o,p,W,H,handle,from,to){const dx=to.x-from.x,dy=to.y-from.y,g=geometry(p,W,H);const orig={x:o.x,y:o.y,w:o.w,h:o.h,rotation:o.rotation||0,shear:o.shear||0,pivot_x:o.pivot_x||0,pivot_y:o.pivot_y||0};
 if(handle==='move')return {...orig,x:clamp(o.x+dx/W,-2,3),y:clamp(o.y+dy/H,-2,3)};
 // Tool modes also accept dragging anywhere inside the selected object. The
 // explicit corner/edge handles below remain available for precise scaling.
 if(handle==='scale-free'){
  const k=clamp(Math.exp((dx+dy)/Math.max(100,g.w,g.h)),Math.max(.02/o.w,.02/o.h),Math.min(2/o.w,2/o.h));
  return {...orig,w:o.w*k,h:o.h*k,x:clamp(o.x+orig.pivot_x*p.w*(1-k)/W,-2,3),y:clamp(o.y+orig.pivot_y*p.h*(1-k)/H,-2,3)};
 }
 if(handle==='rotate-free')return {...orig,rotation:((orig.rotation+dx*360/W+540)%360)-180};
 if(handle==='shear-free')return {...orig,shear:clamp(orig.shear+2*dx/W,-2,2)};
 if(handle==='rotate'){const a=Math.atan2(from.y-g.pivot.y,from.x-g.pivot.x),b=Math.atan2(to.y-g.pivot.y,to.x-g.pivot.x);return {...orig,rotation:((orig.rotation+(b-a)*180/Math.PI+540)%360)-180};}
 if(handle==='shear'){const r=(p.rz||0)*Math.PI/180,den=g.h*(.5-(p.pivot_y||0));if(Math.abs(den)<1e-6)return orig;return {...orig,shear:clamp(orig.shear+(dx*Math.cos(r)+dy*Math.sin(r))/den,-2,2)};}
 if(handle==='pivot'){const v=inverseVector(g.m,dx,dy);const px=clamp(orig.pivot_x+v.x/g.w,-.5,.5),py=clamp(orig.pivot_y+v.y/g.h,-.5,.5);const next=affine({...p,pivot_x:px,pivot_y:py},g.w,g.h);return {...orig,pivot_x:px,pivot_y:py,x:clamp(o.x+(g.m[4]-next[4])/W,-2,3),y:clamp(o.y+(g.m[5]-next[5])/H,-2,3)};}
 const [hx,hy]=handle.split(',').map(Number);if(![-1,0,1].includes(hx)||![-1,0,1].includes(hy)||!hx&&!hy)return orig;
 const v=inverseVector(g.m,dx,dy);let w=o.w,h=o.h;
 if(hx&&hy){const a=hx*g.w/2,b=hy*g.h/2,k=clamp(1+(a*v.x+b*v.y)/(a*a+b*b),Math.max(.02/w,.02/h),Math.min(2/w,2/h));w*=k;h*=k;}
 else {if(hx)w=clamp(w+2*hx*v.x/W/(p.w/o.w),.02,2);if(hy)h=clamp(h+2*hy*v.y/H/(p.h/o.h),.02,2);}
 // Preserve world pivot while scaling, including a custom pivot.
 return {...orig,w,h,x:clamp(o.x+orig.pivot_x*(p.w-p.w*w/o.w),-2,3),y:clamp(o.y+orig.pivot_y*(p.h-p.h*h/o.h),-2,3)};
}
