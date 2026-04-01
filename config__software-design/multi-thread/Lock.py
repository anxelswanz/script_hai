import threading
import time
counter = 0


def increment():
    global counter
    for _ in range(100):
        time.sleep(0.000001)
        temp = counter
        counter = temp + 1


threads = []
for _ in range(2):
    t = threading.Thread(target=increment)
    threads.append(t)
    t.start()


#它告诉主线程（也就是运行你这段代码的“老板”线程）：“先别往后执行，等这个子线程（工人）把活干完了，你再继续。”
for t in threads:
    t.join()

print(f"最终计数: {counter}")