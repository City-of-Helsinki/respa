const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyPlugin = require('copy-webpack-plugin');

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
    userForm: './static_src/js/userFormIndex.js',
    unitForm: './static_src/js/unitFormIndex.js',
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
    }),
    new CopyPlugin([
      { from: './static_src/img/', to: './img/' }
    ])
  ],
  resolve: {
    alias: {
      // For some reason there are multiple jQuery versions, leading to datepicker events not working properly
      // added this to force all modules to use the same jQuery version
      'jquery': path.join(__dirname, 'node_modules/jquery/src/jquery')
    }
  }
};
