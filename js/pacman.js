// 小绿吃豆人游戏 - 性能优化版
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const scoreEl = document.getElementById('score');
    const pelletsEl = document.getElementById('pellets');
    const livesEl = document.getElementById('lives');
    const startBtn = document.getElementById('startBtn');
    const restartBtn = document.getElementById('restartBtn');
    const gameMessage = document.getElementById('gameMessage');
    const messageTitle = document.getElementById('messageTitle');
    const messageText = document.getElementById('messageText');
    const playAgainBtn = document.getElementById('playAgainBtn');

    // 游戏配置
    const TILE_SIZE = 40;
    const MAP_WIDTH = 14;
    const MAP_HEIGHT = 15;
    const CANVAS_WIDTH = MAP_WIDTH * TILE_SIZE;
    const CANVAS_HEIGHT = MAP_HEIGHT * TILE_SIZE;

    // 地图: 0=空地, 1=墙, 2=豆子
    const MAP_TEMPLATE = new Uint8Array([
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,2,2,2,2,2,1,2,2,2,2,2,2,1,
        1,2,1,1,1,2,1,2,1,1,1,1,2,1,
        1,2,1,2,2,2,2,2,2,2,2,1,2,1,
        1,2,2,2,1,1,1,1,1,1,2,2,2,1,
        1,1,1,2,2,2,2,2,2,2,2,1,1,1,
        1,2,2,2,1,1,2,2,1,1,2,2,2,1,
        1,2,1,2,2,2,2,2,2,2,2,1,2,1,
        1,2,1,1,1,2,1,2,1,1,1,1,2,1,
        1,2,2,2,2,2,1,2,2,2,2,2,2,1,
        1,2,1,1,1,2,2,2,1,1,1,1,2,1,
        1,2,2,2,2,2,2,2,2,2,2,2,2,1,
        1,2,1,1,2,1,1,1,1,2,1,1,2,1,
        1,2,2,2,2,2,2,2,2,2,2,2,2,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1
    ]);

    // 离屏canvas缓存静态地图（性能优化关键）
    const staticCanvas = document.createElement('canvas');
    staticCanvas.width = CANVAS_WIDTH;
    staticCanvas.height = CANVAS_HEIGHT;
    const staticCtx = staticCanvas.getContext('2d');

    // 预计算墙壁位置集合，快速碰撞检测
    const wallSet = new Set();

    // 游戏状态 - 使用对象减少内存分配
    let map;
    let player = { x: 6, y: 10, dx: 0, dy: 0, ndx: 0, ndy: 0, moveTimer: 0 };
    let ghosts;
    let score = 0;
    let lives = 3;
    let totalPellets = 0;
    let gameRunning = false;
    let lastTime = 0;
    let animationFrame = null;
    let cachedScore = -1;
    let cachedPellets = -1;
    let cachedLives = -1;
    const MOVE_SPEED = 150;
    const GHOST_SPEEDS = [200, 220];
    const DIRS = [
        { x: 0, y: -1 }, // UP
        { x: 0, y: 1 },  // DOWN
        { x: -1, y: 0 }, // LEFT
        { x: 1, y: 0 }   // RIGHT
    ];

    // 预计算墙壁位置
    function precomputeWalls() {
        wallSet.clear();
        for (let y = 0; y < MAP_HEIGHT; y++) {
            for (let x = 0; x < MAP_WIDTH; x++) {
                if (MAP_TEMPLATE[y * MAP_WIDTH + x] === 1) {
                    wallSet.add(y * MAP_WIDTH + x);
                }
            }
        }
    }

    // 内联碰撞检测 - 直接使用预计算集合
    function isWall(x, y) {
        return x < 0 || x >= MAP_WIDTH || y < 0 || y >= MAP_HEIGHT || wallSet.has(y * MAP_WIDTH + x);
    }

    // 初始化地图和静态缓存
    function initMap() {
        map = new Uint8Array(MAP_TEMPLATE);
        totalPellets = 0;
        for (let i = 0; i < map.length; i++) {
            if (map[i] === 2) totalPellets++;
        }
        precomputeWalls();
        renderStaticMap();
    }

    // 预渲染静态地图（墙和豆子）到离屏canvas - 只在初始化和吃豆子时调用
    function renderStaticMap() {
        staticCtx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // 绘制墙 - 一次性渲染
        staticCtx.fillStyle = '#006400';
        staticCtx.strokeStyle = '#228B22';
        staticCtx.lineWidth = 2;

        for (let y = 0; y < MAP_HEIGHT; y++) {
            for (let x = 0; x < MAP_WIDTH; x++) {
                const tile = map[y * MAP_WIDTH + x];
                const px = x * TILE_SIZE;
                const py = y * TILE_SIZE;

                if (tile === 1) {
                    staticCtx.fillRect(px, py, TILE_SIZE, TILE_SIZE);
                    staticCtx.strokeRect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4);
                } else if (tile === 2) {
                    staticCtx.fillStyle = '#90EE90';
                    staticCtx.beginPath();
                    staticCtx.arc(px + TILE_SIZE/2, py + TILE_SIZE/2, 4, 0, Math.PI * 2);
                    staticCtx.fill();
                    staticCtx.fillStyle = '#006400'; // 恢复墙颜色
                }
            }
        }
    }

    function initPlayer() {
        player.x = 6;
        player.y = 10;
        player.dx = 0;
        player.dy = 0;
        player.ndx = 0;
        player.ndy = 0;
        player.moveTimer = 0;
    }

    function initGhosts() {
        ghosts = [
            { x: 6, y: 7, dx: 0, dy: -1, color: '#FFB6C1', moveTimer: 0, speed: GHOST_SPEEDS[0] },
            { x: 7, y: 7, dx: 0, dy: 1, color: '#FF6B9D', moveTimer: 0, speed: GHOST_SPEEDS[1] }
        ];
    }

    function movePlayer(deltaTime) {
        player.moveTimer += deltaTime;
        if (player.moveTimer < MOVE_SPEED) return;
        player.moveTimer = 0;

        // 尝试切换方向 - 复用计算
        if (player.ndx !== 0 || player.ndy !== 0) {
            const nx = player.x + player.ndx;
            const ny = player.y + player.ndy;
            if (!isWall(nx, ny)) {
                player.dx = player.ndx;
                player.dy = player.ndy;
                player.ndx = 0;
                player.ndy = 0;
            }
        }

        // 移动
        const nx = player.x + player.dx;
        const ny = player.y + player.dy;
        if (!isWall(nx, ny)) {
            player.x = nx;
            player.y = ny;

            // 吃豆子 - 直接索引访问
            const idx = player.y * MAP_WIDTH + player.x;
            if (map[idx] === 2) {
                map[idx] = 0;
                score += 10;
                totalPellets--;

                // 只重绘当前格子而不是整个地图
                const px = player.x * TILE_SIZE;
                const py = player.y * TILE_SIZE;
                staticCtx.clearRect(px, py, TILE_SIZE, TILE_SIZE);

                if (totalPellets === 0) {
                    endGame(true);
                }
            }
        }
    }

    function moveGhosts(deltaTime) {
        const px = player.x;
        const py = player.y;

        for (let i = 0; i < ghosts.length; i++) {
            const ghost = ghosts[i];
            ghost.moveTimer += deltaTime;
            if (ghost.moveTimer < ghost.speed) continue;
            ghost.moveTimer = 0;

            // 预计算反方向
            const odx = -ghost.dx;
            const ody = -ghost.dy;

            // 获取可能方向 - 避免创建数组
            let bestDir = null;
            let minDist = Infinity;
            let randDir = null;
            let dirCount = 0;

            for (let d = 0; d < 4; d++) {
                const dir = DIRS[d];
                // 不能往回走（除非死路）
                if (dir.x === odx && dir.y === ody) continue;

                const nx = ghost.x + dir.x;
                const ny = ghost.y + dir.y;
                if (!isWall(nx, ny)) {
                    dirCount++;
                    const dist = Math.abs(nx - px) + Math.abs(ny - py);
                    if (dist < minDist) {
                        minDist = dist;
                        bestDir = dir;
                    }
                    // 30%概率随机选择
                    if (Math.random() < 0.3 / dirCount || randDir === null) {
                        randDir = dir;
                    }
                }
            }

            if (dirCount === 0) {
                // 死路，掉头
                ghost.dx = odx;
                ghost.dy = ody;
            } else if (Math.random() < 0.7 && bestDir) {
                ghost.dx = bestDir.x;
                ghost.dy = bestDir.y;
            } else if (randDir) {
                ghost.dx = randDir.x;
                ghost.dy = randDir.y;
            }

            ghost.x += ghost.dx;
            ghost.y += ghost.dy;
        }
    }

    function checkCollisions() {
        for (let i = 0; i < ghosts.length; i++) {
            const ghost = ghosts[i];
            if (ghost.x === player.x && ghost.y === player.y) {
                lives--;
                if (lives <= 0) {
                    endGame(false);
                } else {
                    initPlayer();
                    initGhosts();
                }
                break;
            }
        }
    }

    // 仅绘制动态元素，从静态缓存复制背景
    function draw() {
        // 复制静态地图（墙和豆子）- 比逐帧绘制快得多
        ctx.drawImage(staticCanvas, 0, 0);

        // 绘制玩家
        const pPx = player.x * TILE_SIZE + TILE_SIZE/2;
        const pPy = player.y * TILE_SIZE + TILE_SIZE/2;
        const r = TILE_SIZE/2 - 4;

        // 嘴巴角度 - 减少计算
        const time = Date.now() * 0.01;
        const mouthAngle = (Math.sin(time) * 0.2 + 0.2) * Math.PI;

        ctx.fillStyle = '#32CD32';
        ctx.beginPath();

        // 方向旋转 - 简单计算角度
        let angleOffset = 0;
        if (player.dy < 0) angleOffset = Math.PI * 1.5;
        else if (player.dy > 0) angleOffset = Math.PI * 0.5;
        else if (player.dx < 0) angleOffset = Math.PI;

        ctx.moveTo(pPx, pPy);
        ctx.arc(pPx, pPy, r, mouthAngle + angleOffset, Math.PI * 2 - mouthAngle + angleOffset);
        ctx.closePath();
        ctx.fill();

        // 眼睛
        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(pPx - 5, pPy - 8, 3, 0, Math.PI * 2);
        ctx.fill();

        // 绘制幽灵 - 预计算波浪，减少路径操作
        for (let i = 0; i < ghosts.length; i++) {
            const ghost = ghosts[i];
            const gx = ghost.x * TILE_SIZE + TILE_SIZE/2;
            const gy = ghost.y * TILE_SIZE + TILE_SIZE/2;
            const gr = TILE_SIZE/2 - 4;

            ctx.fillStyle = ghost.color;
            ctx.beginPath();
            ctx.arc(gx, gy - 3, gr, Math.PI, 0);
            ctx.lineTo(gx + gr, gy + TILE_SIZE/2 - 8);

            // 简化波浪绘制
            const waveWidth = (TILE_SIZE - 8)/3;
            ctx.lineTo(gx + gr - waveWidth, gy + TILE_SIZE/2 - 14);
            ctx.lineTo(gx + gr - waveWidth * 2, gy + TILE_SIZE/2 - 8);
            ctx.lineTo(gx - gr, gy + TILE_SIZE/2 - 8);

            ctx.closePath();
            ctx.fill();

            // 眼睛
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(gx - 6, gy - 5, 4, 0, Math.PI * 2);
            ctx.arc(gx + 6, gy - 5, 4, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#006400';
            ctx.beginPath();
            ctx.arc(gx - 6, gy - 5, 2, 0, Math.PI * 2);
            ctx.arc(gx + 6, gy - 5, 2, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // 批量更新UI，减少DOM操作
    function updateUI() {
        if (score !== cachedScore) {
            scoreEl.textContent = score;
            cachedScore = score;
        }
        if (totalPellets !== cachedPellets) {
            pelletsEl.textContent = totalPellets;
            cachedPellets = totalPellets;
        }
        if (lives !== cachedLives) {
            livesEl.textContent = lives;
            cachedLives = lives;
        }
    }

    function gameLoopFn(timestamp) {
        if (!gameRunning) return;
        const deltaTime = timestamp - lastTime;
        lastTime = timestamp;

        movePlayer(deltaTime);
        moveGhosts(deltaTime);
        checkCollisions();
        updateUI();
        draw();

        animationFrame = requestAnimationFrame(gameLoopFn);
    }

    function startGame() {
        initMap();
        initPlayer();
        initGhosts();
        score = 0;
        lives = 3;
        cachedScore = -1;
        cachedPellets = -1;
        cachedLives = -1;
        updateUI();
        gameRunning = true;
        startBtn.style.display = 'none';
        restartBtn.style.display = 'inline-block';
        gameMessage.style.display = 'none';
        lastTime = performance.now();
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = requestAnimationFrame(gameLoopFn);
    }

    function endGame(win) {
        gameRunning = false;
        cancelAnimationFrame(animationFrame);
        messageTitle.textContent = win ? '🎉 恭喜获胜！' : '💔 游戏结束';
        messageText.textContent = win
            ? `太棒了！你吃完了所有豆子，最终得分：${score}分`
            : `被幽灵抓住啦！最终得分：${score}分`;
        gameMessage.style.display = 'block';
    }

    // 键盘输入 - 直接设置方向，减少函数调用
    document.addEventListener('keydown', (e) => {
        if (!gameRunning) return;
        switch(e.key) {
            case 'ArrowUp': player.ndx = 0; player.ndy = -1; e.preventDefault(); break;
            case 'ArrowDown': player.ndx = 0; player.ndy = 1; e.preventDefault(); break;
            case 'ArrowLeft': player.ndx = -1; player.ndy = 0; e.preventDefault(); break;
            case 'ArrowRight': player.ndx = 1; player.ndy = 0; e.preventDefault(); break;
        }
    });

    // 移动端控制
    document.getElementById('btnUp').addEventListener('click', () => { if(gameRunning) { player.ndx = 0; player.ndy = -1; }});
    document.getElementById('btnDown').addEventListener('click', () => { if(gameRunning) { player.ndx = 0; player.ndy = 1; }});
    document.getElementById('btnLeft').addEventListener('click', () => { if(gameRunning) { player.ndx = -1; player.ndy = 0; }});
    document.getElementById('btnRight').addEventListener('click', () => { if(gameRunning) { player.ndx = 1; player.ndy = 0; }});

    startBtn.addEventListener('click', startGame);
    restartBtn.addEventListener('click', startGame);
    playAgainBtn.addEventListener('click', startGame);

    // 初始渲染
    initMap();
    initPlayer();
    initGhosts();
    updateUI();
    draw();
});
