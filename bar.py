from matplotlib import pyplot as plt


def show(names, weights):
    _, ax = plt.subplots(figsize =(16, 9))

    ax.barh(names, weights)

    for s in ['top', 'bottom', 'left', 'right']:
        ax.spines[s].set_visible(False)

    ax.xaxis.set_tick_params(pad = 5)
    ax.yaxis.set_tick_params(pad = 10)

    ax.grid(
        b = True, 
        color ='black',
        linestyle ='-.', linewidth = 0.5,
        alpha = 0.2)

    ax.invert_yaxis()

    for patch in ax.patches:
        plt.text(
            patch.get_width() + 0.1,
            patch.get_y() + 0.5, 
            str(round((patch.get_width()), 2)),
            fontsize = 10, 
            fontweight ='bold',
            color ='grey')

    ax.set_title('Топ коммитеры', loc ='center', )

    plt.show()