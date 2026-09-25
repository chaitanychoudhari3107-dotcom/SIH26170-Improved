import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';
export function useApi(endpoint, options = { immediate: true }) {
  const [data,setData]=useState(null),[loading,setLoading]=useState(options.immediate),[error,setError]=useState(null);
  const pending=useRef(null);
  const execute=useCallback(async()=>{
    pending.current?.abort();
    if(!endpoint)return;
    const controller=new AbortController();pending.current=controller;
    setLoading(true);setError(null);
    try{const result=await api.get(endpoint,{signal:controller.signal});if(!controller.signal.aborted)setData(result);}
    catch(err){if(!controller.signal.aborted)setError(err);}
    finally{if(!controller.signal.aborted)setLoading(false);}
  },[endpoint]);
  useEffect(()=>{setData(null);if(options.immediate&&endpoint)execute();return()=>pending.current?.abort();},[execute,options.immediate,endpoint]);
  return {data,loading,error,refetch:execute};
}
