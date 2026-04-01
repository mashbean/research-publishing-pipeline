# Automation Contract

## Goal

研究文章 job 一旦啟動，就自動進入強制 active reminder 模式；只有結案或明確失敗時才退出。

## Start semantics

當使用者下達啟動研究文章任務的指令時，系統應在建立 job 後立刻同步更新 `memory/automation-state.json`：

- `activeWork = true`
- `mode = "active"`
- `taskTitle = <job id 或文章題目>`
- `taskNote = <本次任務描述>`
- `nextDeliverable = <最近一步最小交付物>`
- `lastMeaningfulProgressAt = now`
- `lastUpdated = now`

## While running

- 10 分鐘 active checker 持續觸發
- 若無新進展，必須先做一個 safe self-push，再回報
- 30 分鐘 stall watchdog 若判定卡住，必須升級回報 blocked reason 與 recovery action

## End semantics

當 job 狀態進入下列任一條件時，系統應更新 `memory/automation-state.json` 並退出 active 模式：

- `verified`
- `publish-failed`
- `verification-failed`
- `blocked`
- 明確人工結案

退出時應寫入：

- `activeWork = false`
- `mode = "idle"`
- 清空 `taskTitle` / `taskNote` / `nextDeliverable`
- 保留 `lastDeliverable`
- 更新 `lastDeliverableAt` / `lastMeaningfulProgressAt` / `lastUpdated`

## Acceptance target

豆泥只要下啟動指令，文章 job 就自己往下跑，並在沒有結束前維持 10 分鐘強制提醒模式，不需要額外再補一句「請繼續」。
