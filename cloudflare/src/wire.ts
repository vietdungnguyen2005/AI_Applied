import {Validator,type Schema} from "@cfworker/json-schema";
import contract from "../../src/vmarket_ai/gateway/wire.json";
const cache=new Map<string,Validator>();
export function valid(name:keyof typeof contract.$defs,input:unknown):boolean{
  let validator=cache.get(name);
  if(!validator){validator=new Validator({...contract,$ref:"#/$defs/"+name} as Schema,"2020-12",true);cache.set(name,validator);}
  return validator.validate(input).valid;
}
