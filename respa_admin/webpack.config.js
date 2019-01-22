const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

const CssRule = {
  test: /\.(scss)$/,
  use: ['style-loader', 'css-loader', 'sass-loader'],
  include: path.resolve(__dirname, './views')
};

module.exports = {
  entry: {
    main: './static_src/styles/base.scss',
    styles: './static_src/js/styles.js',
    resourceForm: './static_src/js/resourceFormIndex.js',
    base: './static_src/js/baseIndex.js',
  },
  output: {
    filename: '[name]-bundle.js',
    path: path.resolve(__dirname, './static/respa_admin/'),
  },
  module: {
    // Add loader
    rules: [
      {
        test: /\.(scss)$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader', 'sass-loader']
      },
      {
        test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
        use: [{
        loader: 'file-loader',
          options: {
            name: '[name].[ext]',
            outputPath: 'fonts/'
          }
        }]
      }
    ]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: "[name].css",
      chunkFilename: "[id].css"
    })
  ]
};
