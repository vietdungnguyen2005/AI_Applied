import { DatabaseSync, type SQLInputValue } from "node:sqlite";
import { readFileSync } from "node:fs";
import type { Database, Statement, SqlValue } from "../src/spec";

export class TestDatabase implements Database {
  readonly raw = new DatabaseSync(":memory:");
  constructor() {this.raw.exec(readFileSync(new URL("../schema.sql",import.meta.url),"utf8"));}
  prepare(sql: string): Statement {
    const database=this.raw;
    function make(values: SqlValue[]): Statement {
      const args=values.map((v): SQLInputValue => v instanceof ArrayBuffer ? new Uint8Array(v) : v);
      return {
        bind: (...bound) => make(bound),
        async first<T>() {return (database.prepare(sql).get(...args) as T|undefined)??null;},
        async all<T>() {return {results: database.prepare(sql).all(...args) as T[]};},
        async run() {const r=database.prepare(sql).run(...args);return {success:true,meta:{changes:Number(r.changes)}};},
      };
    }
    return make([]);
  }
  async batch(statements: Statement[]) {
    this.raw.exec("BEGIN");
    try {const result=[];for(const statement of statements)result.push(await statement.run());this.raw.exec("COMMIT");return result;}
    catch(error) {this.raw.exec("ROLLBACK");throw error;}
  }
}
