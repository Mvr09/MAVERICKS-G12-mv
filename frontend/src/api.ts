let csrf='';
export function setCsrf(v:string){csrf=v}
export async function api<T=any>(path:string, options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers);
 if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
 if(options.method && options.method!=='GET') headers.set('X-CSRF-Token',csrf);
 const response=await fetch('/api'+path,{...options,headers,credentials:'same-origin'});
 if(!response.ok){const e=await response.json().catch(()=>({message:'Error de conexión'}));throw new Error(e.message||'No se pudo completar la operación')}
 return response.json();
}
export const date=(v?:string)=>v?new Intl.DateTimeFormat('es-ES',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Madrid'}).format(new Date(v)):'Sin consultar';
export const number=(v:number|null|undefined)=>v==null?'—':v.toLocaleString('es-ES',{maximumFractionDigits:1});
