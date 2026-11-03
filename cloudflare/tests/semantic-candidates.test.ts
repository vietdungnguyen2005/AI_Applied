import {expect,it} from "vitest";
import {profileColumns} from "../src/column-profile";
import {semanticCandidates} from "../src/semantic-candidates";
it("selects a unique explicit physical quantity while excluding reserved units",()=>{
  const columns=profileColumns(["PhysicalQuantity","ReservedQuantity"],[["12","2"],["8","1"]]);
  expect(semanticCandidates(columns,{})).toEqual({on_hand:"PhysicalQuantity"});
});
it("selects a unique product display-text candidate without mistaking numeric units for a name",()=>{
  const columns=profileColumns(["SKU","DisplayText","Quantity"],[["P-1","Desk","12"],["P-2","Bag","4"]]);
  expect(semanticCandidates(columns,{sku:"SKU"})).toEqual({name:"DisplayText"});
});
it("leaves an apparently explicit physical column unresolved when sampled rows contradict its integer contract",()=>{
  const columns=profileColumns(["PhysicalQuantity"],[["12"],["not a count"]]);
  expect(semanticCandidates(columns,{})).toEqual({});
});
it("does not mistake a physical-item numeric identifier for an inventory count",()=>{
  const columns=profileColumns(["PhysicalItemID"],[["12"],["23"]]);
  expect(semanticCandidates(columns,{})).toEqual({});
});
