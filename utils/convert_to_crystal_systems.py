import pandas as pd
import circlify
import matplotlib.pyplot as plt
import seaborn as sns

df_keys = pd.read_csv('data/auto_magined_key.csv')

# Mapping ITC number to crystal system
def assign_crystal_system(itc_number):
    if 1 <= itc_number <= 2:
        return "triclinic"
    elif 3 <= itc_number <= 15:
        return "monoclinic"
    elif 16 <= itc_number <= 74:
        return "orthorhombic"
    elif 75 <= itc_number <= 142:
        return "tetragonal"
    elif 143 <= itc_number <= 167:
        return "trigonal"
    elif 168 <= itc_number <= 194:
        return "hexagonal"
    elif 195 <= itc_number <= 230:
        return "cubic"
    else:
        return "unknown"

df_keys['crystal_system'] = df_keys['symmetry_Int_Tables_number'].apply(assign_crystal_system)

df_counts = df_keys['crystal_system'].value_counts()

df_counts_df = pd.DataFrame({'crystal_system': df_counts.index, 'counts': df_counts.values})


circles = circlify.circlify(df_counts_df['counts'].tolist(),
                            show_enclosure=False,
                            target_enclosure=circlify.Circle(x=0, y=0)
                           )
circles.reverse()


list_country = df_counts_df.crystal_system.values
pal_ = list(sns.color_palette(palette='Set2',
                              n_colors=len(list_country)).as_hex())
label = [ i+'<br>'+str(j) for i, j in zip(df_counts_df.crystal_system.values, df_counts_df.counts.values )]


fig, ax = plt.subplots(figsize=(8,8), facecolor='white')
ax.axis('off')
lim = max(max(abs(circle.x)+circle.r, abs(circle.y)+circle.r,) for circle in circles)
plt.xlim(-lim, lim)
plt.ylim(-lim, lim)

for circle, note, color in zip(circles, label, pal_):
    x, y, r = circle
    ax.add_patch(plt.Circle((x, y), r, alpha=1, color = color))
    plt.annotate(note.replace('<br>','\n'), (x,y), size=16, va='center', ha='center')
plt.xticks([])
plt.yticks([])
plt.savefig('circlefy_crystal_systems.svg', dpi=600)
plt.show()