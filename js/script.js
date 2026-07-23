// 小绿博客脚本 - 飘落叶子动画
document.addEventListener('DOMContentLoaded', function() {
    const leavesContainer = document.getElementById('leaves');
    const leafEmojis = ['🍃', '🌿', '🍀', '🌱', '☘️'];

    // 创建飘落的叶子
    function createLeaf() {
        const leaf = document.createElement('div');
        leaf.className = 'leaf';
        leaf.textContent = leafEmojis[Math.floor(Math.random() * leafEmojis.length)];
        leaf.style.left = Math.random() * 100 + 'vw';
        leaf.style.animationDuration = (Math.random() * 5 + 5) + 's';
        leaf.style.fontSize = (Math.random() * 10 + 15) + 'px';
        leavesContainer.appendChild(leaf);

        // 动画结束后移除
        setTimeout(() => {
            leaf.remove();
        }, 10000);
    }

    // 定期生成叶子
    setInterval(createLeaf, 800);

    // 初始生成几个
    for (let i = 0; i < 5; i++) {
        setTimeout(createLeaf, i * 200);
    }

    // 导航栏平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    console.log('%c🌱 小绿的博客加载完成啦！', 'color: #228B22; font-size: 16px; font-weight: bold;');
    console.log('%c绿色上网，花季护航 💚', 'color: #32CD32; font-size: 14px;');

    // ========== 随机小绿图片功能 ==========
    // gmp3 小绿图片库 - 静态资源列表（GitHub Pages无需后端）
    // 后续添加更多图片，只需在这里加文件名即可
    const xiaoluImages = [
        'img/gallery/xiaolu_avatar.jpg',
        'img/gallery/lvba_1.jpg',
        'img/gallery/lvba_2.jpg'
    ];

    let currentImageIndex = 0;
    const randomImageEl = document.getElementById('randomXiaoluImage');
    const refreshBtn = document.getElementById('refreshImageBtn');

    function getRandomImage() {
        let newIndex;
        // 确保不重复当前图片
        do {
            newIndex = Math.floor(Math.random() * xiaoluImages.length);
        } while (newIndex === currentImageIndex && xiaoluImages.length > 1);

        currentImageIndex = newIndex;

        // 添加淡入动画
        randomImageEl.style.opacity = '0';
        setTimeout(() => {
            randomImageEl.src = xiaoluImages[currentImageIndex];
            randomImageEl.style.opacity = '1';
        }, 200);
    }

    // 初始化随机显示一张
    getRandomImage();

    // 点击按钮刷新
    if (refreshBtn) {
        refreshBtn.addEventListener('click', getRandomImage);
    }

    // 点击图片也可以刷新
    if (randomImageEl) {
        randomImageEl.addEventListener('click', getRandomImage);
        randomImageEl.style.cursor = 'pointer';
    }
});
