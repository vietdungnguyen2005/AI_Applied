/** Deterministic, bounded context; original bytes and authoritative header names stay untouched. */
export function profileColumns(headers:string[],rows:string[][]){
  const count=Math.min(50,rows.length);
  const selected=Array.from({length:count},(_,i)=>rows[count===1?0:Math.round(i*(rows.length-1)/(count-1))]);
  return headers.map((header,index)=>{
    const values=selected.map(row=>row[index]),nonempty=values.filter(v=>Boolean(v.trim()));
    const distinct=[...new Set(nonempty)];
    const examples=Array.from({length:Math.min(5,distinct.length)},(_,i)=>{
      const position=distinct.length<=5?i:Math.round(i*(distinct.length-1)/4);
      return distinct[position].slice(0,80);
    });
    const ratio=(test:(v:string)=>boolean)=>nonempty.length?nonempty.filter(v=>test(v.trim())).length/nonempty.length:null;
    return {header,sample_count:count,non_empty_count:nonempty.length,empty_ratio:count?(count-nonempty.length)/count:0,
      distinct_ratio:nonempty.length?distinct.length/nonempty.length:null,
      integer_ratio:ratio(v=>/^[+-]?[0-9]+$/.test(v)),quantity_ratio:ratio(v=>/^[0-9]{1,7}$/.test(v)&&Number(v)<=1000000),
      min_length:nonempty.length?Math.min(...nonempty.map(v=>[...v].length)):0,
      max_length:nonempty.length?Math.max(...nonempty.map(v=>[...v].length)):0,
      examples,examples_truncated:distinct.some(v=>v.length>80)};
  });
}
