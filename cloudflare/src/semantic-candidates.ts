import type {profileColumns} from "./column-profile";
type Target="sku"|"name"|"on_hand";
/** Conservative schema-meaning rules, not approved aliases or learned holdout headers. */
export function semanticCandidates(columns:ReturnType<typeof profileColumns>,known:Partial<Record<Target,string>>):Partial<Record<Target,string>>{
  const result:Partial<Record<Target,string>>={};
  if(!known.on_hand){
    const matches=columns.filter(c=>!Object.values(known).includes(c.header)&&
      /physical|on[\s_-]*hand|現物|実在庫|棚卸/iu.test(c.header)&&
      /quantity|count|units|stock|inventory|qty|balance|在庫|棚卸|数量/iu.test(c.header)&&
      !/reserved|allocated|available|sellable|price|cost|forecast|planned|identifier|code|reference|sku|id$|length|width|weight|引当|予約|販売可能|金額|単価|予定|識別|コード|重量|長さ/iu.test(c.header)&&
      c.non_empty_count>0&&c.quantity_ratio===1);
    if(matches.length===1)result.on_hand=matches[0].header;
  }
  if(!known.name){
    const matches=columns.filter(c=>!Object.values({...known,...result}).includes(c.header)&&
      /display|label|title|name|description|名称|商品名|品名|表示/iu.test(c.header)&&
      !/supplier|vendor|warehouse|location|address|email|note|comment|仕入先|取引先|倉庫|住所|備考|メモ/iu.test(c.header)&&
      c.non_empty_count>0&&c.integer_ratio===0&&c.max_length<=160);
    if(matches.length===1)result.name=matches[0].header;
  }
  return result;
}
