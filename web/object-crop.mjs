// Operação sobre recursos de imagem. A composição continua usando o mesmo
// objeto da timeline; apenas a mídia derivada é substituída e a fonte preservada.
export function normalizeCrop(raw){
 if(!Array.isArray(raw)||raw.length!==4)return [0,0,1,1];
 const a=raw.map(Number);if(a.some(x=>!Number.isFinite(x)))throw Error('Recorte inválido.');
 const [x,y,w,h]=a;if(x<0||y<0||w<=0||h<=0||x+w>1.00001||y+h>1.00001)throw Error('Recorte fora da imagem.');
 return [x,y,w,h];
}
export async function cropImageURL(url,crop,{maxSide=2048}={}){
 const [x,y,w,h]=normalizeCrop(crop);
 const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Imagem original indisponível.'));image.src=url;});
 const sw=image.naturalWidth*w,sh=image.naturalHeight*h;if(sw<=0||sh<=0)throw Error('Área de recorte vazia.');
 const scale=Math.min(1,maxSide/Math.max(sw,sh));const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(sw*scale));canvas.height=Math.max(1,Math.round(sh*scale));
 const ctx=canvas.getContext('2d');if(!ctx)throw Error('Canvas de recorte indisponível.');
 ctx.drawImage(image,x*image.naturalWidth,y*image.naturalHeight,sw,sh,0,0,canvas.width,canvas.height);
 return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('Falha ao gerar recorte.')),'image/png'));
}
