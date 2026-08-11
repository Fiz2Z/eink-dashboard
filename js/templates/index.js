/**
 * Template registry — 新增模板：
 * 1. 新建 js/templates/xxx.js 并 export 一个 template 对象
 * 2. 在本文件 import 并加入 templates 数组
 */
import { tokenTemplate } from "./token.js";
import { statusTemplate } from "./status.js";
import { quoteTemplate } from "./quote.js";

/** @type {import('./base.js') extends never ? any : Array} */
export const templates = [tokenTemplate, statusTemplate, quoteTemplate];

export function getTemplate(id) {
  return templates.find((t) => t.id === id) || templates[0];
}
