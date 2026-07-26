// 小绿吃豆人游戏 - 匹配博客绿色主题
document.addEventListener('DOMContentLoaded', function() {
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

    // 地图: 0=空地, 1=墙, 2=豆子
    const MAP_TEMPLATE = [
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        [1,2,2,2,2,2,1,2,2,2,2,2,2,1],
        [1,2,1,1,1,2,1,2,1,1,1,1,2,1],
        [1,2,1,2,2,2,2,2,2,2,2,1,2,1],
        [1,2,2,2,1,1,1,1,1,1,2,2,2,1],
        [1,1,1,2,2,2,2,2,2,2,2,1,1,1],
        [1,2,2,2,1,1,2,2,1,1,2,2,2,1],
        [1,2,1,2,2,2,2,2,2,2,2,1,2,1],
        [1,2,1,1,1,2,1,2,1,1,1,1,2,1],
        [1,2,2,2,2,2,1,2,2,2,2,2,2,1],
        [1,2,1,1,1,2,2,2,1,1,1,1,2,1],
        [1,2,2,2,2,2,2,2,2,2,2,2,2,1],
        [1,2,1,1,2,1,1,1,1,2,1,1,2,1],
        [1,2,2,2,2,2,2,2,2,2,2,2,2,1],
        [1,1,1,1,1,1,1,1,1,1,1,1,1,1]
    ];

    // 游戏状态
    let map = [];
    let player = {};
    let ghosts = [];
    let score = 0;
    let lives = 3;
    let totalPellets = 0;
    let gameRunning = false;
    let gameLoop = null;
    let keys = {};
    let lastTime = 0;
    const MOVE_SPEED = 150; // 移动速度ms per tile

    // 方向定义
    const DIRECTIONS = {
        UP: { x: 0, y: -1 },
        DOWN: { x: 0, y: 1 },
        LEFT: { x: -1, y: 0 },
        RIGHT: { x: 1, y: 0 },
        NONE: { x: 0, y: 0 }
    };

    // 初始化游戏地图
    function initMap() {
        map = MAP_TEMPLATE.map(row => [...row]);
        totalPellets = 0;
        for (let y = 0; y < MAP_HEIGHT; y++) {
            for (let x = 0; x < MAP_WIDTH; x++) {
                if (map[y][x] === 2) totalPellets++;
            }
        }
    }

    // 初始化玩家
    function initPlayer() {
        player = {
            x: 6,
            y: 10,
            direction: DIRECTIONS.NONE,
            nextDirection: DIRECTIONS.NONE,
            moveTimer: 0
        };
    }

    // 初始化幽灵
    function initGhosts() {
        ghosts = [
            { x: 6, y: 7, direction: DIRECTIONS.UP, color: '#FFB6C1', moveTimer: 0, speed: 200 }, // 粉色幽灵1
            { x: 7, y: 7, direction: DIRECTIONS.DOWN, color: '#FF6B9D', moveTimer: 0, speed: 220 }  // 深粉幽灵2
        ];
    }

    // 检测墙壁碰撞
    function isWall(x, y) {
        if (x < 0 || x >= MAP_WIDTH || y < 0 || y >= MAP_HEIGHT) return true;
        return map[y][x] === 1;
    }

    // 处理玩家移动
    function movePlayer(deltaTime) {
        player.moveTimer += deltaTime;
        if (player.moveTimer < MOVE_SPEED) return;
        player.moveTimer = 0;

        // 尝试切换方向
        if (player.nextDirection !== DIRECTIONS.NONE) {
            const newX = player.x + player.nextDirection.x;
            const newY = player.y + player.nextDirection.y;
            if (!isWall(newX, newY)) {
                player.direction = player.nextDirection;
                player.nextDirection = DIRECTIONS.NONE;
            }
        }

        // 移动
        const newX = player.x + player.direction.x;
        const newY = player.y + player.direction.y;
        if (!isWall(newX, newY)) {
            player.x = newX;
            player.y = newY;

            // 吃豆子
            if (map[player.y][player.x] === 2) {
                map[player.y][player.x] = 0;
                score += 10;
                totalPellets--;
                updateUI();

                // 吃完所有豆子获胜
                if (totalPellets === 0) {
                    endGame(true);
                }
            }
        }
    }

    // 幽灵AI - 简单追踪玩家 + 随机移动
    function moveGhosts(deltaTime) {
        ghosts.forEach(ghost => {
            ghost.moveTimer += deltaTime;
            if (ghost.moveTimer < ghost.speed) return;
            ghost.moveTimer = 0;

            // 获取所有可移动方向
            const possibleDirs = [];
            Object.values(DIRECTIONS).forEach(dir => {
                if (dir === DIRECTIONS.NONE) return;
                const newX = ghost.x + dir.x;
                const newY = ghost.y + dir.y;
                // 不能往回走
                if (dir.x === -ghost.direction.x && dir.y === -ghost.direction.y) return;
                if (!isWall(newX, newY)) {
                    possibleDirs.push(dir);
                }
            });

            if (possibleDirs.length === 0) {
                // 死路，掉头
                ghost.direction = { x: -ghost.direction.x, y: -ghost.direction.y };
            } else {
                // 70%概率朝玩家方向走，30%随机
                let bestDir = possibleDirs[0];
                if (Math.random() < 0.7) {
                    let minDist = Infinity;
                    possibleDirs.forEach(dir => {
                        const newX = ghost.x + dir.x;
                        const newY = ghost.y + dir.y;
                        const dist = Math.abs(newX - player.x) + Math.abs(newY - player.y);
                        if (dist < minDist) {
                            minDist = dist;
                            bestDir = dir;
                        }
                    });
                } else {
                    bestDir = possibleDirs[Math.floor(Math.random() * possibleDirs.length)];
                }
                ghost.direction = bestDir;
            }

            ghost.x += ghost.direction.x;
            ghost.y += ghost.direction.y;
        });
    }

    // 检测碰撞
    function checkCollisions() {
        ghosts.forEach(ghost => {
            if (ghost.x === player.x && ghost.y === player.y) {
                lives--;
                updateUI();
                if (lives <= 0) {
                    endGame(false);
                } else {
                    // 重置位置
                    initPlayer();
                    initGhosts();
                }
            }
        });
    }

    // 绘制游戏
    function draw() {
        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 绘制地图
        for (let y = 0; y < MAP_HEIGHT; y++) {
            for (let x = 0; x < MAP_WIDTH; x++) {
                const tile = map[y][x];
                const px = x * TILE_SIZE;
                const py = y * TILE_SIZE;

                if (tile === 1) {
                    // 墙 - 深绿色
                    ctx.fillStyle = '#006400';
                    ctx.fillRect(px, py, TILE_SIZE, TILE_SIZE);
                    // 边框高光
                    ctx.strokeStyle = '#228B22';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4);
                } else if (tile === 2) {
                    // 豆子 - 浅绿色
                    ctx.fillStyle = '#90EE90';
                    ctx.beginPath();
                    ctx.arc(px + TILE_SIZE/2, py + TILE_SIZE/2, 4, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }

        // 绘制玩家（绿色吃豆人）
        const playerPx = player.x * TILE_SIZE + TILE_SIZE/2;
        const playerPy = player.y * TILE_SIZE + TILE_SIZE/2;
        ctx.fillStyle = '#32CD32';
        ctx.beginPath();
        // 嘴巴动画
        const mouthAngle = (Math.sin(Date.now() / 100) * 0.2 + 0.2) * Math.PI;
        let startAngle = mouthAngle;
        let endAngle = Math.PI * 2 - mouthAngle;
        // 根据方向旋转
        if (player.direction === DIRECTIONS.UP) {
            startAngle += Math.PI * 1.5;
            endAngle += Math.PI * 1.5;
        } else if (player.direction === DIRECTIONS.DOWN) {
            startAngle += Math.PI * 0.5;
            endAngle += Math.PI * 0.5;
        } else if (player.direction === DIRECTIONS.LEFT) {
            startAngle += Math.PI;
            endAngle += Math.PI;
        }
        ctx.moveTo(playerPx, playerPy);
        ctx.arc(playerPx, playerPy, TILE_SIZE/2 - 4, startAngle, endAngle);
        ctx.closePath();
        ctx.fill();
        // 眼睛
        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(playerPx - 5, playerPy - 8, 3, 0, Math.PI * 2);
        ctx.fill();

        // 绘制幽灵
        ghosts.forEach(ghost => {
            const gx = ghost.x * TILE_SIZE + TILE_SIZE/2;
            const gy = ghost.y * TILE_SIZE + TILE_SIZE/2;
            ctx.fillStyle = ghost.color;
            // 幽灵身体
            ctx.beginPath();
            ctx.arc(gx, gy - 3, TILE_SIZE/2 - 4, Math.PI, 0);
            ctx.lineTo(gx + TILE_SIZE/2 - 4, gy + TILE_SIZE/2 - 8);
            // 波浪底边
            for (let i = 0; i < 3; i++) {
                const waveX = gx + TILE_SIZE/2 - 4 - (i + 1) * (TILE_SIZE - 8)/3;
                const waveY = gy + TILE_SIZE/2 - 8 - (i % 2 === 0 ? 6 : 0);
                ctx.lineTo(waveX, waveY);
            }
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
        });
    }

    // 更新UI
    function updateUI() {
        scoreEl.textContent = score;
        pelletsEl.textContent = totalPellets;
        livesEl.textContent = lives;
    }

    // 游戏主循环
    function gameLoopFn(timestamp) {
        if (!gameRunning) return;
        const deltaTime = timestamp - lastTime;
        lastTime = timestamp;

        movePlayer(deltaTime);
        moveGhosts(deltaTime);
        checkCollisions();
        draw();

        requestAnimationFrame(gameLoopFn);
    }

    // 开始游戏
    function startGame() {
        initMap();
        initPlayer();
        initGhosts();
        score = 0;
        lives = 3;
        updateUI();
        gameRunning = true;
        startBtn.style.display = 'none';
        restartBtn.style.display = 'inline-block';
        gameMessage.style.display = 'none';
        lastTime = performance.now();
        if (gameLoop) cancelAnimationFrame(gameLoop);
        gameLoop = requestAnimationFrame(gameLoopFn);
    }

    // 结束游戏
    function endGame(win) {
        gameRunning = false;
        cancelAnimationFrame(gameLoop);
        if (win) {
            messageTitle.textContent = '🎉 恭喜获胜！';
            messageText.textContent = `太棒了！你吃完了所有豆子，最终得分：${score}分`;
        } else {
            messageTitle.textContent = '💔 游戏结束';
            messageText.textContent = `被幽灵抓住啦！最终得分：${score}分`;
        }
        gameMessage.style.display = 'block';
    }

    // 键盘事件
    document.addEventListener('keydown', (e) => {
        if (!gameRunning) return;
        switch(e.key) {
            case 'ArrowUp':
                player.nextDirection = DIRECTIONS.UP;
                e.preventDefault();
                break;
            case 'ArrowDown':
                player.nextDirection = DIRECTIONS.DOWN;
                e.preventDefault();
                break;
            case 'ArrowLeft':
                player.nextDirection = DIRECTIONS.LEFT;
                e.preventDefault();
                break;
            case 'ArrowRight':
                player.nextDirection = DIRECTIONS.RIGHT;
                e.preventDefault();
                break;
        }
    });

    // 移动端控制
    document.getElementById('btnUp').addEventListener('click', () => { if(gameRunning) player.nextDirection = DIRECTIONS.UP; });
    document.getElementById('btnDown').addEventListener('click', () => { if(gameRunning) player.nextDirection = DIRECTIONS.DOWN; });
    document.getElementById('btnLeft').addEventListener('click', () => { if(gameRunning) player.nextDirection = DIRECTIONS.LEFT; });
    document.getElementById('btnRight').addEventListener('click', () => { if(gameRunning) player.nextDirection = DIRECTIONS.RIGHT; });

    // 按钮事件
    startBtn.addEventListener('click', startGame);
    restartBtn.addEventListener('click', startGame);
    playAgainBtn.addEventListener('click', startGame);

    // 初始绘制空白地图
    initMap();
    initPlayer();
    initGhosts();
    updateUI();
    draw();
});
