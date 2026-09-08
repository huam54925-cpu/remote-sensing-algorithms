# 第二算法示例的来源与复现

来源：scikit-learn 官方示例 [Comparison of the K-Means and MiniBatchKMeans clustering algorithms](https://scikit-learn.org/stable/auto_examples/cluster/plot_mini_batch_kmeans.html)。
使用 scikit-learn 1.9.0 提供的 KMeans（BSD-3-Clause），依赖随镜像携带各自的 dist-info 许可证。项目的 GeoTIFF 适配和测试是本次新编写，未复制整份上游绘图代码。

复现方式：沿用官方示例的 make_blobs 合成数据与 KMeans 调用方式，固定三个中心、随机种子、n_init、迭代上限和线程数；省略绘图及 MiniBatchKMeans 比较，加入 GeoTIFF 编解码与 NoData。这是官方算法调用的适配复现，不声称原样重现其图表或耗时。

tests/create_kmeans_fixture.py 生成 90×90、两波段、三个可分离簇的影像和预期类别，额外设置一个 NoData 像元。
测试独立直接调用 sklearn KMeans，并以 adjusted_rand_score 比较容器适配结果及生成器真值，避免任意类别编号置换带来的误判。
另验证 CRS、仿射变换、像元有效数、类型和 NoData。该样本不是实际卫星数据，不用于证明业务精度。

CPU-only，未安装 GPU 计算框架。此示例无需训练权重和运行联网。实际算法的授权、权重许可证、数据来源和发布许可需收到代码时另行核对。
