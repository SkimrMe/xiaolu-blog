// 读取json文件
fetch('data/navbar.json')
.then(response => {
    return response.json();
})
.then(data => {
    const json_home = data[0];
    const json_articles = data[1];
    const json_diary = data[2];
    const json_gallery = data[3];
    const json_video = data[4];
    const json_game = data[5];
    const json_memories = data[6];
    const json_rumors = data[7];
    const json_about = data[8];

    // Vue  循环
    Vue.createApp({
        data() {
            return {
                list: [
                    json_home,
                    json_articles,
                    json_diary,
                    json_gallery,
                    json_video,
                    json_game,
                    json_memories,
                    json_rumors,
                    json_about,
                ]
            }
        }
    }).mount('#navbar');
});