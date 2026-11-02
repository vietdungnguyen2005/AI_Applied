export function strictJson(text: string): unknown {
  const stack: ({keys: Set<string>; key: boolean} | null)[] = [];
  for (let i=0; i<text.length; i++) {
    const c=text[i];
    if (c==='"') {
      const start=i; i++;
      while (i<text.length && text[i]!=='"') {if(text[i]==='\\')i++;i++;}
      const object=stack.at(-1);
      if (object?.key) {
        const key: string=JSON.parse(text.slice(start,i+1));
        if (object.keys.has(key)) throw new Error("duplicate JSON key");
        object.keys.add(key);object.key=false;
      }
    } else if(c==="{")stack.push({keys:new Set(),key:true});
    else if(c==="[")stack.push(null);
    else if(c==="}"||c==="]")stack.pop();
    else if(c===",") {const object=stack.at(-1);if(object)object.key=true;}
    if(stack.length>64)throw new Error("JSON nesting limit");
  }
  return JSON.parse(text,(_,value:unknown)=>{
    if(typeof value==="number"&&!Number.isFinite(value))throw new Error("nonfinite JSON value");
    return value;
  });
}
