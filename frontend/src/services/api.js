const BASE_URL = import.meta.env.VITE_API_URL || '';
let token = '';
async function request(endpoint, options = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`} : {}),...options.headers}});
  if (!response.ok) {
    const data = await response.json().catch(()=>null);
    const d=data?.detail;
    const message=typeof d==='string'?d:Array.isArray(d)?d.map(x=>x.msg).join('; '):d?.message;
    const error=new Error(message||data?.message||`Request failed (${response.status})`);error.status=response.status;throw error;
  }
  return response;
}
export const api={
  setToken:value=>{token=value;},
  get:async(endpoint,options={})=>(await request(endpoint,options)).json(),
  post:async(endpoint,body)=>(await request(endpoint,{method:'POST',body:JSON.stringify(body)})).json(),
  download:async(endpoint,name)=>{const blob=await (await request(endpoint)).blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);},
};
