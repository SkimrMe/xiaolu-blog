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
});
