const gulp        = require('gulp');
const browserSync = require('browser-sync');
const sass        = require('gulp-sass')(require('sass'));
const cleanCSS = require('gulp-clean-css');
const autoprefixer = require('autoprefixer')
const postcss = require('gulp-postcss');
const rename = require("gulp-rename");

gulp.task('server', function() {

    browserSync({
        server: {
            baseDir: "Uber_project"
        }
    });

    gulp.watch("Uber_project/*.html").on('change', browserSync.reload);
});

gulp.task('styles', function() {
    return gulp.src("Uber_project/sass/**/*.+(scss|sass)")
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(rename({suffix: '.min', prefix: ''}))
        .pipe(postcss([ autoprefixer() ]))
        .pipe(cleanCSS({compatibility: 'ie8'}))
        .pipe(gulp.dest("Uber_project/css"));
        // .pipe(browserSync.stream());
});

gulp.task('watch', function() {
    gulp.watch("Uber_project/sass/**/*.+(scss|sass)", gulp.parallel('styles'));
})

gulp.task('default', gulp.parallel('watch', 'server', 'styles'));