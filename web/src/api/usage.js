/** 用量与额度接口：当日输出 token 额度快照。 */

import { request } from './client.js'

/**
 * 当日输出 token 额度快照。
 * @returns {Promise<{limit:number,used:number,remaining:number,exceeded:boolean,resetAt:string,day:string,timezone:string}>}
 */
export function fetchUsage() {
  return request('/api/usage/today')
}
