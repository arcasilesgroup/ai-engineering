// Concurrent queue with backpressure for the async sidecar. Processes jobs
// with bounded concurrency; rejects when the queue is full. Inspired by
// Pyro's ConcurrentQueue (DelvisorLabs/Pyro packages/queue/src/index.ts).

export interface QueueSnapshot {
  active: number;
  waiting: number;
  concurrency: number;
  maxDepth: number;
  accepted: number;
  completed: number;
  failed: number;
  rejected: number;
}

export class QueueFullError extends Error {
  constructor() {
    super("Queue is at capacity. Retry later.");
    this.name = "QueueFullError";
  }
}

export interface QueueResult<T> {
  id: string;
  value: T;
  queueMs: number;
}

export class ConcurrentQueue {
  // Jobs of different generic types share this queue. The resolve/reject are
  // called with the correct type at execution time; the array just holds refs.
  private readonly waiting: Array<{ id: string; enqueuedAt: number; execute: (queueMs: number) => Promise<unknown>; resolve: (value: QueueResult<unknown>) => void; reject: (reason: unknown) => void }> = [];
  private active = 0;
  private accepted = 0;
  private completed = 0;
  private failed = 0;
  private rejected = 0;

  constructor(
    private readonly concurrency: number,
    private readonly maxDepth: number,
  ) {}

  /** Submit a job. Returns a promise that resolves when the job completes.
   *  Throws QueueFullError when the queue is at capacity. */
  submit<T>(execute: (queueMs: number) => Promise<T>, id: string = crypto.randomUUID()): Promise<QueueResult<T>> {
    if (this.active + this.waiting.length >= this.maxDepth + this.concurrency) {
      this.rejected += 1;
      throw new QueueFullError();
    }
    this.accepted += 1;
    return new Promise<QueueResult<T>>((resolve, reject) => {
      this.waiting.push({
        id,
        enqueuedAt: Date.now(),
        execute: execute as (queueMs: number) => Promise<unknown>,
        resolve: resolve as (value: QueueResult<unknown>) => void,
        reject,
      });
      this.drain();
    });
  }

  snapshot(): QueueSnapshot {
    return {
      active: this.active,
      waiting: this.waiting.length,
      concurrency: this.concurrency,
      maxDepth: this.maxDepth,
      accepted: this.accepted,
      completed: this.completed,
      failed: this.failed,
      rejected: this.rejected,
    };
  }

  private drain(): void {
    while (this.active < this.concurrency && this.waiting.length > 0) {
      const job = this.waiting.shift()!;
      this.active += 1;
      const queueMs = Date.now() - job.enqueuedAt;
      job
        .execute(queueMs)
        .then((value) => {
          this.active -= 1;
          this.completed += 1;
          job.resolve({ id: job.id, value, queueMs });
          this.drain();
        })
        .catch((error) => {
          this.active -= 1;
          this.failed += 1;
          job.reject(error);
          this.drain();
        });
    }
  }
}
